# app/tools/rag/vector_service.py
"""核心 RAG 检索服务:BGE-M3 密集检索 + jieba 关键词兜底。

并发模型(Stage 1 重构后):
- query 编码无锁(torch.inference_mode 下只读前向,并发安全)。
- "检查 dirty → 重建 → 替换"在 _reindex_lock 临界区内完成,末尾用单一不可变
  快照 _IndexSnapshot 原子替换 self._snapshot,杜绝读到半截状态。
- 模型懒加载受 _load_lock 双检锁保护。
"""
import hashlib
import json
import os
import threading
from dataclasses import dataclass

import jieba
import numpy as np

from app.tools.rag import config
from app.common.db import SessionLocal
from app.tools.rag.models import KnowledgeItem


@dataclass(frozen=True)
class _IndexSnapshot:
    """某一时刻索引的不可变快照。重建时整体替换,读者只持引用,无需加锁。"""
    knowledge_items: tuple
    documents: tuple
    embeddings: object  # np.ndarray 或 None
    ready: bool


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
        self.use_fp16 = config.RAG_USE_FP16
        self.batch_size = config.RAG_BATCH_SIZE
        self.max_length = config.RAG_MAX_LENGTH
        self.retrieval_top_k = config.RAG_RETRIEVAL_TOP_K
        self.min_retrieval_score = config.RAG_RETRIEVAL_MIN_SCORE
        self.query_prefix = config.RAG_QUERY_PREFIX
        self.strict_threshold = config.RAG_STRICT_THRESHOLD

        self.embedding_model = None
        self.embedding_tokenizer = None
        self.device = None
        self.model_error = None
        self.pooling = config.RAG_POOLING

        self._snapshot = _IndexSnapshot((), (), None, False)
        self._dirty = True

        self._load_lock = threading.Lock()        # 保护模型懒加载
        self._reindex_lock = threading.RLock()    # 保护"检查 dirty→重建→替换"临界区

        # 索引持久化(Stage 3)
        self._cache_dir = config.RAG_CACHE_DIR
        self._cache_disabled = config.RAG_CACHE_DISABLED
        self._cache_npy = self._cache_dir / 'rag_index_embeddings.npy'
        self._cache_meta = self._cache_dir / 'rag_index_meta.json'

    # ------------------------------------------------------------------ #
    # 模型加载
    # ------------------------------------------------------------------ #
    def _load_embedding_model(self):
        if self.embedding_model is not None:
            return
        with self._load_lock:
            if self.embedding_model is not None:   # 再查,防并发重复加载
                return
            import torch
            from transformers import AutoModel, AutoTokenizer

            if config.RAG_TORCH_NUM_THREADS:
                torch.set_num_threads(config.RAG_TORCH_NUM_THREADS)

            self.device = self._resolve_device(torch)
            torch_dtype = self._resolve_torch_dtype(torch)

            self.embedding_tokenizer = AutoTokenizer.from_pretrained(self.embedding_model_name, trust_remote_code=True)
            self.embedding_model = AutoModel.from_pretrained(
                self.embedding_model_name,
                trust_remote_code=True,
                torch_dtype=torch_dtype,
            )
            self.embedding_model.eval()
            # Stage 4: CPU 下可选 INT8 动态量化(opt-in,默认关)。失败静默回退 fp32。
            if config.RAG_INT8_QUANTIZE and str(self.device).startswith('cpu'):
                try:
                    self.embedding_model = torch.quantization.quantize_dynamic(
                        self.embedding_model, {torch.nn.Linear}, dtype=torch.qint8
                    )
                except Exception:
                    pass  # 量化失败不影响服务,保持 fp32
            self.embedding_model.to(self.device)

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

        # 无锁。torch.inference_mode 下前向只读模型参数,query 编码可并发。
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

    # ------------------------------------------------------------------ #
    # 索引持久化(Stage 3)
    # ------------------------------------------------------------------ #
    def _config_fingerprint(self):
        """影响 embedding 语义的配置指纹。换模型/pooling/max_length/前缀/量化必须重建。"""
        parts = [
            self.embedding_model_name,
            self.pooling,
            str(self.max_length),
            self.query_prefix,
            'int8' if config.RAG_INT8_QUANTIZE else 'fp',
        ]
        return hashlib.sha1('|'.join(parts).encode('utf-8')).hexdigest()

    def _item_fingerprints(self, items):
        """每条知识项的内容指纹(无 updated_at,自算)。返回 {id: sha1}。"""
        fp = {}
        for item in items:
            raw = f"{item.id}|{item.title}|{item.content}|{item.category}|{item.is_indexed}"
            fp[str(item.id)] = hashlib.sha1(raw.encode('utf-8')).hexdigest()
        return fp

    def _aggregate_fingerprint(self, config_hash, item_fps):
        """聚合指纹:config_hash + 排序后的 per-item 指纹。任一条目变更即变化。"""
        ordered = json.dumps(item_fps, sort_keys=True, ensure_ascii=False)
        return hashlib.sha1(f"{config_hash}|{ordered}".encode('utf-8')).hexdigest()

    def _try_load_cache(self, items):
        """尝试从磁盘加载缓存。命中且校验通过返回 documents,否则 None。

        全程容错:任何异常/不匹配都返回 None,由调用方走全量编码。
        """
        if self._cache_disabled:
            return None
        try:
            if not (self._cache_npy.exists() and self._cache_meta.exists()):
                return None
            with open(self._cache_meta, 'r', encoding='utf-8') as f:
                meta = json.load(f)

            config_hash = self._config_fingerprint()
            if meta.get('config_hash') != config_hash:
                return None

            cur_item_fps = self._item_fingerprints(items)
            cur_agg = self._aggregate_fingerprint(config_hash, cur_item_fps)
            if meta.get('aggregate_fingerprint') != cur_agg:
                return None

            embeddings = np.load(self._cache_npy)
            expected_dim = meta.get('dim')
            expected_count = meta.get('count')
            if expected_count != len(items):
                return None
            if embeddings.shape[0] != len(items):
                return None
            if expected_dim is not None and embeddings.shape[1] != expected_dim:
                return None

            # 按 meta 中记录的 id 顺序重排 embeddings,对齐当前 items 顺序。
            cached_order = [int(i) for i in meta['item_order']]
            cur_ids = [item.id for item in items]
            if cached_order != cur_ids:
                pos = {cid: idx for idx, cid in enumerate(cached_order)}
                embeddings = np.array([embeddings[pos[cid]] for cid in cur_ids])

            documents = tuple(self._build_document_text(item) for item in items)
            return documents, embeddings.astype(np.float32)
        except Exception:
            return None

    def _persist_cache(self, items, documents, embeddings):
        """原子落盘:写临时文件后 os.replace 改名,防半截文件。"""
        if self._cache_disabled or embeddings is None or not documents:
            return
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            config_hash = self._config_fingerprint()
            item_fps = self._item_fingerprints(items)
            item_order = [str(item.id) for item in items]
            meta = {
                'config_hash': config_hash,
                'aggregate_fingerprint': self._aggregate_fingerprint(config_hash, item_fps),
                'item_fps': item_fps,        # 保留 per-item hash,为未来增量编码铺路
                'item_order': item_order,
                'dim': int(embeddings.shape[1]) if embeddings.ndim == 2 else 0,
                'count': int(embeddings.shape[0]),
            }
            tmp_npy = str(self._cache_npy) + '.tmp'
            tmp_meta = str(self._cache_meta) + '.tmp'
            # np.save 会强制追加 .npy 后缀,故用文件对象写入避免双重后缀。
            with open(tmp_npy, 'wb') as buf:
                np.save(buf, embeddings.astype(np.float32))
            with open(tmp_meta, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False)
            os.replace(tmp_npy, self._cache_npy)
            os.replace(tmp_meta, self._cache_meta)
        except Exception:
            pass  # 持久化失败不影响检索功能

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
        # 可选 query 前缀(BGE-M3 实测不敏感,默认空串)。拼接在实体增强之前。
        base = f"{self.query_prefix}{query}" if self.query_prefix else query
        entities = self.extract_entities(query)
        entity_hint = []
        for entity_list in entities.values():
            entity_hint.extend(entity_list * 2)
        if not entity_hint:
            return base
        return f"{base}\n相关景区实体：{' '.join(entity_hint)}"

    def ensure_index(self):
        """确保索引就绪。脏或未就绪则重建;重建在 _reindex_lock 内原子完成。"""
        if not self._dirty and self._snapshot.ready:
            return
        with self._reindex_lock:
            if not self._dirty and self._snapshot.ready:   # 再查,防并发重复重建
                return
            self._rebuild_locked()

    def _rebuild_locked(self):
        """全量重建:全部在局部变量算好后,末尾单次原子替换 self._snapshot。

        必须在 _reindex_lock 持有期间调用。
        """
        try:
            session = SessionLocal()
            try:
                items = tuple(session.query(KnowledgeItem).filter_by(is_indexed=True).all())
            finally:
                session.close()
        except Exception as exc:
            self.model_error = str(exc)
            return 0

        documents = tuple(self._build_document_text(item) for item in items)
        embeddings = None
        if documents:
            # 先试缓存:命中则免编码(冷启动从 ~5.8s 降到 ~0.1s)。
            cached = self._try_load_cache(items)
            if cached is not None:
                documents, embeddings = cached
                self.model_error = None
            else:
                try:
                    embeddings = self._encode_texts(list(documents))
                    self.model_error = None
                    self._persist_cache(items, documents, embeddings)
                except Exception as exc:
                    self.model_error = str(exc)

        # 单次原子绑定:CPython GIL 保证读线程看到的要么是旧快照要么是新快照。
        self._snapshot = _IndexSnapshot(items, documents, embeddings, ready=True)
        self._dirty = False
        return len(documents)

    def sync_all_knowledge(self):
        """强制重建索引(router /reindex 直调)。"""
        with self._reindex_lock:
            self._dirty = True
            return self._rebuild_locked()

    def index_status(self):
        try:
            session = SessionLocal()
            try:
                total = session.query(KnowledgeItem).count()
                indexed = session.query(KnowledgeItem).filter_by(is_indexed=True).count()
            finally:
                session.close()
        except Exception:
            snap = self._snapshot
            total = len(snap.knowledge_items)
            indexed = len(snap.knowledge_items)

        return {
            'total_items': total,
            'indexed_items': indexed,
            'index_ready': self._snapshot.ready,
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
        snap = self._snapshot
        if not snap.documents:
            return []

        if snap.embeddings is None:
            return self._keyword_search(query, snap)[:top_k]

        try:
            results = self._dense_search(query, top_k, snap)
        except Exception as exc:
            self.model_error = str(exc)
            results = []

        if results:
            return results

        return self._keyword_search(query, snap)[:top_k]

    def _dense_search(self, query, top_k, snap):
        enhanced_query = self._enhance_query(query)
        query_vector = self._encode_texts([enhanced_query])[0]
        similarities = np.matmul(snap.embeddings, query_vector)

        candidate_limit = max(top_k, self.retrieval_top_k)
        ranked_indices = np.argsort(similarities)[::-1][:candidate_limit]
        candidates = [
            (int(index), float(similarities[index]))
            for index in ranked_indices
            if float(similarities[index]) >= self.min_retrieval_score
        ]

        # 非严格模式下:过滤后为空则回退取相似度>0 的 top_k(旧行为,会硬塞无关结果)。
        # 严格模式默认开启:不回退,空就空,交给 search 的关键词兜底。
        if not candidates and not self.strict_threshold:
            candidates = [
                (int(index), float(similarities[index]))
                for index in ranked_indices[:top_k]
                if float(similarities[index]) > 0
            ]

        if not candidates:
            return []

        return [
            self._format_result(index, score=retrieval_score, source_type='bge_m3', retrieval_score=retrieval_score, snap=snap)
            for index, retrieval_score in candidates[:top_k]
        ]

    def _format_result(self, index, score, source_type, retrieval_score=None, snap=None):
        snap = snap or self._snapshot
        item = snap.knowledge_items[index]
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
        return result

    def _keyword_search(self, query, snap):
        results = []
        keywords = jieba.lcut(query)
        for item in snap.knowledge_items:
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
