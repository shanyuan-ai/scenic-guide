# app/tools/rag/vector_service.py
"""核心 RAG 检索服务:BGE-M3 密集检索 + bge-reranker-v2-m3 交叉编码重排。

检索逻辑(向量召回、重排、关键词兜底、热词缓存、实体增强)保持不变,
仅调整了 import 路径以适配新的 tools/ 目录结构。
"""
import threading

import jieba
import numpy as np

from app.tools.rag import config
from app.common.db import SessionLocal
from app.tools.rag.models import KnowledgeItem


class VectorService:
    def __init__(self):
        self.scenic_entities = {
            '景点': ['灵山大佛', '九龙灌浴', '梵宫', '五印坛城', '祥符禅寺', '佛手广场', '曼飞龙塔', '灵山精舍'],
            '活动': ['抱佛脚', '摸佛掌', '撞钟', '转经筒', '祈福'],
            '文化': ['佛教', '禅意', '藏传佛教', '汉传佛教', '五方五佛'],
            '实用': ['门票', '开放时间', '路线', '素斋', '住宿'],
        }

        self.hot_questions_cache = {
            "门票": "灵山胜境门票参考价格为210元/人（具体以景区公告为准），包含灵山大佛、九龙灌浴、梵宫等主要景点。",
            "门票多少钱": "灵山胜境门票参考价格为210元/人，学生、老人等优惠政策请咨询景区。",
            "开放时间": "灵山胜境开放时间为每天7:30-17:30（旺季可能延长，建议提前查询）。",
            "几点开门": "灵山胜境开放时间为每天7:30-17:30。",
            "怎么去": "可乘坐公交88路、89路直达灵山胜境，或自驾导航'灵山胜境停车场'。",
        }

        self.embedding_model_name = config.RAG_EMBEDDING_MODEL
        self.reranker_model_name = config.RAG_RERANKER_MODEL
        self.use_fp16 = config.RAG_USE_FP16
        self.batch_size = config.RAG_BATCH_SIZE
        self.max_length = config.RAG_MAX_LENGTH
        self.retrieval_top_k = config.RAG_RETRIEVAL_TOP_K
        self.min_retrieval_score = config.RAG_RETRIEVAL_MIN_SCORE

        self.embedding_model = None
        self.embedding_tokenizer = None
        self.reranker = None
        self.reranker_tokenizer = None
        self.device = None
        self.knowledge_items = []
        self.documents = []
        self.embeddings = None
        self.model_error = None
        self._index_ready = False
        self._dirty = True

        self.reranker_max_length = config.RAG_RERANKER_MAX_LENGTH
        self.pooling = config.RAG_POOLING
        self._model_lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # 模型加载
    # ------------------------------------------------------------------ #
    def _load_embedding_model(self):
        if self.embedding_model is not None:
            return
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.device = self._resolve_device(torch)
        torch_dtype = self._resolve_torch_dtype(torch)

        self.embedding_tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_name, trust_remote_code=True)
        self.embedding_model = AutoModel.from_pretrained(
            self.embedding_model_name,
            trust_remote_code=True,
            torch_dtype=torch_dtype,
        )
        self.embedding_model.eval()
        self.embedding_model.to(self.device)

    def _load_reranker(self):
        if self.reranker is not None:
            return
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if self.device is None:
            self.device = self._resolve_device(torch)

        torch_dtype = self._resolve_torch_dtype(torch)

        self.reranker_tokenizer = AutoTokenizer.from_pretrained(self.reranker_model_name, trust_remote_code=True)
        self.reranker = AutoModelForSequenceClassification.from_pretrained(
            self.reranker_model_name,
            trust_remote_code=True,
            torch_dtype=torch_dtype,
        )
        self.reranker.eval()
        self.reranker.to(self.device)

    def _resolve_device(self, torch_module):
        configured = config.RAG_DEVICE
        if configured and configured != 'auto':
            return torch_module.device(configured)
        return torch_module.device('cuda' if torch_module.cuda.is_available() else 'cpu')

    def _resolve_torch_dtype(self, torch_module):
        if str(self.device).startswith('cuda') and self.use_fp16:
            return torch_module.float16
        return None

    # ------------------------------------------------------------------ #
    # 向量编码
    # ------------------------------------------------------------------ #
    def _normalize_vectors(self, vectors):
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return vectors / norms

    def _encode_texts(self, texts):
        if not texts:
            return np.empty((0, 0), dtype=np.float32)

        self._load_embedding_model()
        import torch

        with self._model_lock:
            tokenizer = self.embedding_tokenizer
            model = self.embedding_model

            effective_max_len = self._effective_max_length(tokenizer, self.max_length)
            vectors = []
            with torch.inference_mode():
                for start in range(0, len(texts), self.batch_size):
                    batch = texts[start:start + self.batch_size]
                    encoded = tokenizer(
                        batch,
                        padding=True,
                        truncation=True,
                        max_length=effective_max_len,
                        return_tensors='pt',
                    )
                    encoded = {k: v.to(self.device) for k, v in encoded.items()}
                    output = model(**encoded, return_dict=True)
                    last_hidden = output.last_hidden_state

                    if self.pooling == 'mean':
                        attention_mask = encoded.get('attention_mask')
                        mask = attention_mask.unsqueeze(-1).expand(last_hidden.size()).float()
                        summed = (last_hidden * mask).sum(dim=1)
                        counts = mask.sum(dim=1).clamp(min=1e-9)
                        pooled = summed / counts
                    else:
                        pooled = last_hidden[:, 0]

                    batch_vec = pooled.detach().float().cpu().numpy().astype(np.float32)
                    vectors.append(batch_vec)

            all_vecs = np.concatenate(vectors, axis=0) if vectors else np.empty((0, 0), dtype=np.float32)
            return self._normalize_vectors(all_vecs)

    def _effective_max_length(self, tokenizer, requested):
        try:
            model_max = int(getattr(tokenizer, 'model_max_length', requested) or requested)
        except Exception:
            model_max = requested
        if model_max > 100000:
            model_max = requested
        return int(min(requested, model_max))

    # ------------------------------------------------------------------ #
    # 索引同步
    # ------------------------------------------------------------------ #
    def mark_dirty(self):
        self._dirty = True

    def _build_document_text(self, item):
        return f"标题：{item.title}\n分类：{item.category_display}\n内容：{item.content}"

    def _tokenize(self, text):
        words = jieba.cut(text)
        result = []
        for word in words:
            result.append(word)
            for entities in self.scenic_entities.values():
                if word in entities:
                    result.extend([word, word])
        return ' '.join(result)

    def extract_entities(self, query):
        found_entities = {}
        for category, entities in self.scenic_entities.items():
            for entity in entities:
                if entity in query:
                    found_entities.setdefault(category, []).append(entity)
        return found_entities

    def check_hot_question(self, query):
        for key, answer in self.hot_questions_cache.items():
            if key in query:
                return answer
        return None

    def _enhance_query(self, query):
        entities = self.extract_entities(query)
        entity_hint = []
        for entity_list in entities.values():
            entity_hint.extend(entity_list * 2)
        if not entity_hint:
            return query
        return f"{query}\n相关景区实体：{' '.join(entity_hint)}"

    def ensure_index(self):
        if self._dirty or not self._index_ready:
            self.sync_all_knowledge()

    def sync_all_knowledge(self):
        try:
            session = SessionLocal()
            try:
                self.knowledge_items = session.query(KnowledgeItem).filter_by(is_indexed=True).all()
            finally:
                session.close()
        except Exception as exc:
            self.model_error = str(exc)
            self._index_ready = False
            return 0

        self.documents = [self._build_document_text(item) for item in self.knowledge_items]
        self.embeddings = None
        self._index_ready = True
        self._dirty = False

        if not self.documents:
            return 0

        try:
            self.embeddings = self._encode_texts(self.documents)
            self.model_error = None
        except Exception as exc:
            self.model_error = str(exc)

        return len(self.documents)

    def index_status(self):
        try:
            session = SessionLocal()
            try:
                total = session.query(KnowledgeItem).count()
                indexed = session.query(KnowledgeItem).filter_by(is_indexed=True).count()
            finally:
                session.close()
        except Exception:
            total = len(self.knowledge_items)
            indexed = len(self.knowledge_items)

        return {
            'total_items': total,
            'indexed_items': indexed,
            'index_ready': self._index_ready,
            'model_error': self.model_error,
        }

    # ------------------------------------------------------------------ #
    # 检索
    # ------------------------------------------------------------------ #
    def search(self, query, top_k=5):
        query = (query or '').strip()
        if not query:
            return []

        cached_answer = self.check_hot_question(query)
        if cached_answer:
            return [{
                'content': cached_answer,
                'title': '高频问题缓存',
                'category': 'hot_question',
                'score': 1.0,
                'source_type': 'cache',
            }]

        self.ensure_index()
        if not self.documents:
            return []

        if self.embeddings is None:
            return self._keyword_search(query)[:top_k]

        try:
            results = self._dense_search(query, top_k)
        except Exception as exc:
            self.model_error = str(exc)
            results = []

        if results:
            return results

        return self._keyword_search(query)[:top_k]

    def _dense_search(self, query, top_k):
        enhanced_query = self._enhance_query(query)
        query_vector = self._encode_texts([enhanced_query])[0]
        similarities = np.matmul(self.embeddings, query_vector)

        candidate_limit = max(top_k, self.retrieval_top_k)
        ranked_indices = np.argsort(similarities)[::-1][:candidate_limit]
        candidates = [
            (int(index), float(similarities[index]))
            for index in ranked_indices
            if float(similarities[index]) >= self.min_retrieval_score
        ]

        if not candidates:
            candidates = [
                (int(index), float(similarities[index]))
                for index in ranked_indices[:top_k]
                if float(similarities[index]) > 0
            ]

        if not candidates:
            return []

        return self._rerank_results(query, candidates, top_k)

    def _rerank_results(self, query, candidates, top_k):
        try:
            self._load_reranker()
            pairs = [[query, self.documents[index]] for index, _ in candidates]
            rerank_scores = self._compute_rerank_scores(pairs)
        except Exception:
            return [
                self._format_result(index, score=retrieval_score, source_type='bge_m3', retrieval_score=retrieval_score)
                for index, retrieval_score in candidates[:top_k]
            ]

        reranked = sorted(
            zip(candidates, rerank_scores),
            key=lambda item: item[1],
            reverse=True,
        )
        return [
            self._format_result(index, score=rerank_score, source_type='bge_m3_reranker', retrieval_score=retrieval_score, rerank_score=rerank_score)
            for (index, retrieval_score), rerank_score in reranked[:top_k]
        ]

    def _compute_rerank_scores(self, pairs):
        self._load_reranker()
        import torch

        tokenizer = self.reranker_tokenizer
        model = self.reranker
        effective_max_len = self._effective_max_length(tokenizer, self.reranker_max_length)

        scores = []
        with self._model_lock:
            with torch.inference_mode():
                for start in range(0, len(pairs), self.batch_size):
                    batch_pairs = pairs[start:start + self.batch_size]
                    inputs = tokenizer(
                        batch_pairs,
                        padding=True,
                        truncation=True,
                        max_length=effective_max_len,
                        return_tensors='pt',
                    )
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    logits = model(**inputs, return_dict=True).logits
                    logits = logits.view(-1).float()
                    probs = torch.sigmoid(logits)
                    scores.extend([float(v) for v in probs.detach().cpu().tolist()])

        return scores

    def _format_result(self, index, score, source_type, retrieval_score=None, rerank_score=None):
        item = self.knowledge_items[index]
        result = {
            'id': item.id,
            'content': item.content,
            'title': item.title,
            'category': item.category,
            'score': float(score),
            'source_type': source_type,
        }
        if retrieval_score is not None:
            result['retrieval_score'] = float(retrieval_score)
        if rerank_score is not None:
            result['rerank_score'] = float(rerank_score)
        return result

    def _keyword_search(self, query):
        results = []
        keywords = jieba.lcut(query)
        for item in self.knowledge_items:
            score = 0
            text = f"{item.title} {item.content}"
            for keyword in keywords:
                if keyword in text and len(keyword) > 1:
                    score += text.count(keyword)
            if score > 0:
                results.append({
                    'id': item.id,
                    'content': item.content,
                    'title': item.title,
                    'category': item.category,
                    'score': min(score / 10, 0.5),
                    'source_type': 'keyword',
                })
        results.sort(key=lambda item: item['score'], reverse=True)
        return results


vector_service = VectorService()
