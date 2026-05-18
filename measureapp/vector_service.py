# measureapp/vector_service.py
import os
import threading

import jieba
import numpy as np
from django.conf import settings

from .models import KnowledgeItem


class VectorService:
    def __init__(self):
        print("正在初始化 BGE-M3 景区知识检索系统...")

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

        self.embedding_model_name = self._resolve_model_name(
            setting_name='RAG_EMBEDDING_MODEL',
            default_repo='BAAI/bge-m3',
            local_dir_name='bge-m3',
        )
        self.reranker_model_name = self._resolve_model_name(
            setting_name='RAG_RERANKER_MODEL',
            default_repo='BAAI/bge-reranker-v2-m3',
            local_dir_name='bge-reranker-v2-m3',
        )
        self.use_fp16 = self._get_bool_setting('RAG_USE_FP16', True)
        self.batch_size = self._get_int_setting('RAG_BATCH_SIZE', 8)
        self.max_length = self._get_int_setting('RAG_MAX_LENGTH', 8192)
        self.retrieval_top_k = self._get_int_setting('RAG_RETRIEVAL_TOP_K', 20)
        self.min_retrieval_score = self._get_float_setting('RAG_RETRIEVAL_MIN_SCORE', 0.2)

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

        self.reranker_max_length = self._get_int_setting('RAG_RERANKER_MAX_LENGTH', 512)
        self.pooling = (getattr(settings, 'RAG_POOLING', os.getenv('RAG_POOLING', 'cls')) or 'cls').strip().lower()
        self._model_lock = threading.Lock()

    def _resolve_model_name(self, setting_name, default_repo, local_dir_name):
        configured = getattr(settings, setting_name, None) or os.getenv(setting_name)
        if configured:
            return configured

        base_dir = getattr(settings, 'BASE_DIR', None)
        if base_dir:
            local_path = base_dir / 'models' / local_dir_name
            if local_path.exists():
                return str(local_path)

        return default_repo

    def _get_bool_setting(self, name, default):
        value = getattr(settings, name, os.getenv(name, default))
        if isinstance(value, bool):
            return value
        return str(value).lower() in {'1', 'true', 'yes', 'on'}

    def _get_int_setting(self, name, default):
        return int(getattr(settings, name, os.getenv(name, default)))

    def _get_float_setting(self, name, default):
        return float(getattr(settings, name, os.getenv(name, default)))

    def _load_embedding_model(self):
        if self.embedding_model is not None:
            return
        try:
            import torch
            from transformers import AutoModel, AutoTokenizer
        except Exception as exc:
            raise RuntimeError(f"缺少 transformers/torch 依赖，无法加载 BGE-M3：{exc}")

        self.device = self._resolve_device(torch)
        torch_dtype = self._resolve_torch_dtype(torch)

        if not self._model_path_exists(self.embedding_model_name):
            raise RuntimeError(
                f"embedding 模型路径不存在且未启用在线下载：{self.embedding_model_name}。"
                f"请先运行 download_model.py，或设置 RAG_ALLOW_REMOTE_DOWNLOAD=1"
            )

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
        try:
            import torch
            from transformers import AutoModelForSequenceClassification, AutoTokenizer
        except Exception as exc:
            raise RuntimeError(f"缺少 transformers/torch 依赖，无法加载 reranker：{exc}")

        if self.device is None:
            self.device = self._resolve_device(torch)

        torch_dtype = self._resolve_torch_dtype(torch)

        if not self._model_path_exists(self.reranker_model_name):
            raise RuntimeError(
                f"reranker 模型路径不存在且未启用在线下载：{self.reranker_model_name}。"
                f"请先运行 download_model.py，或设置 RAG_ALLOW_REMOTE_DOWNLOAD=1"
            )

        self.reranker_tokenizer = AutoTokenizer.from_pretrained(self.reranker_model_name, trust_remote_code=True)
        self.reranker = AutoModelForSequenceClassification.from_pretrained(
            self.reranker_model_name,
            trust_remote_code=True,
            torch_dtype=torch_dtype,
        )
        self.reranker.eval()
        self.reranker.to(self.device)

    def _resolve_device(self, torch_module):
        configured = getattr(settings, 'RAG_DEVICE', None) or os.getenv('RAG_DEVICE')
        if configured:
            return torch_module.device(configured)
        return torch_module.device('cuda' if torch_module.cuda.is_available() else 'cpu')

    def _resolve_torch_dtype(self, torch_module):
        if str(self.device).startswith('cuda') and self.use_fp16:
            return torch_module.float16
        return None

    def _model_path_exists(self, model_name_or_path):
        allow_remote = self._get_bool_setting('RAG_ALLOW_REMOTE_DOWNLOAD', False)
        if allow_remote:
            return True
        # If it's not a local path, force an explicit opt-in to avoid long downloads in dev.
        if model_name_or_path.startswith('http://') or model_name_or_path.startswith('https://'):
            return False
        if os.path.isdir(model_name_or_path):
            return True
        # HuggingFace repo id pattern: contains '/'
        return False

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

    def _build_document_text(self, item):
        category_display = item.get_category_display() if hasattr(item, 'get_category_display') else item.category
        return f"标题：{item.title}\n分类：{category_display}\n内容：{item.content}"

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
        print("正在构建 BGE-M3 景区知识索引...")
        try:
            self.knowledge_items = list(KnowledgeItem.objects.filter(is_indexed=True))
        except Exception as exc:
            self.model_error = str(exc)
            self._index_ready = False
            print(f"知识库读取失败，暂时无法构建索引：{exc}")
            return 0

        self.documents = [self._build_document_text(item) for item in self.knowledge_items]
        self.embeddings = None
        self._index_ready = True
        self._dirty = False

        if not self.documents:
            print("知识库为空，跳过索引")
            return 0

        try:
            self.embeddings = self._encode_texts(self.documents)
            self.model_error = None
            print(f"BGE-M3 索引完成，共 {len(self.documents)} 条知识")
        except Exception as exc:
            self.model_error = str(exc)
            print(f"BGE-M3 索引构建失败，将使用关键词兜底：{exc}")

        return len(self.documents)

    def add_knowledge_item(self, instance=None, *args, **kwargs):
        # Any change could affect the indexed corpus (content update, or indexed flag toggled).
        self._dirty = True
        return 0

    def delete_knowledge_item(self, instance=None, *args, **kwargs):
        # Deletions may shrink the corpus.
        self._dirty = True
        return 0

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
            print(f"BGE-M3 检索失败，将使用关键词兜底：{exc}")
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
        except Exception as exc:
            print(f"bge-reranker-v2-m3 重排失败，将使用 BGE-M3 召回分排序：{exc}")
            return [
                self._format_result(
                    index,
                    score=retrieval_score,
                    source_type='bge_m3',
                    retrieval_score=retrieval_score,
                )
                for index, retrieval_score in candidates[:top_k]
            ]

        reranked = sorted(
            zip(candidates, rerank_scores),
            key=lambda item: item[1],
            reverse=True,
        )
        return [
            self._format_result(
                index,
                score=rerank_score,
                source_type='bge_m3_reranker',
                retrieval_score=retrieval_score,
                rerank_score=rerank_score,
            )
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
