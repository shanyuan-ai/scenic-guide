# app/tools/rag/eval_retrieval.py
"""RAG 检索质量评测脚本(非生产代码)。

对 BGE-M3 的 query 前缀、分数阈值、实体增强做 Recall@5 / MRR@5 对比,
判断某项改动是否带来检索质量收益(默认预期:前缀对 BGE-M3 无显著差异)。

用法:
    python -m app.tools.rag.eval_retrieval

评测集自动从已索引知识库生成:每条文档用其标题作为"伪查询",
期望该文档自身出现在 top-5。这是一种弱监督,足以检测明显回归;
真实标注集应人工编写,但当前 25 条规模下此法可快速给出方向性结论。
"""
import sys

import numpy as np

from app.tools.rag import config as rag_config
from app.tools.rag.vector_service import vector_service


# ---- 评测集 ----
def build_eval_set():
    """从索引库生成 (query, expected_id) 对:每条文档标题作为查询。"""
    vector_service.ensure_index()
    snap = vector_service._snapshot
    pairs = []
    for item in snap.knowledge_items:
        title = item.title.strip()
        if title:
            pairs.append((title, item.id))
    return pairs


# ---- 指标 ----
def _rank_top_k(vector_service_obj, query, expected_id, top_k=5):
    """返回 expected_id 在 top_k 结果中的排名(0=不在)。"""
    # 跳过热词缓存命中(走真实 dense/keyword)
    results = vector_service_obj._dense_search_safe(query, top_k) or []
    ids = [r.get('id') for r in results]
    return ids.index(expected_id) + 1 if expected_id in ids else 0


def evaluate(vs, eval_set, top_k=5):
    recall_hits = 0
    mrr_sum = 0.0
    for query, expected_id in eval_set:
        rank = _rank_top_k(vs, query, expected_id, top_k)
        if rank > 0:
            recall_hits += 1
            mrr_sum += 1.0 / rank
    n = len(eval_set)
    return {
        'n': n,
        'recall@5': recall_hits / n if n else 0.0,
        'mrr@5': mrr_sum / n if n else 0.0,
    }


def main():
    # 给 vector_service 打个补丁:_dense_search 直接调用(绕过热词缓存与 dirty 检查)
    def _dense_search_safe(self, query, top_k):
        snap = self._snapshot
        if not snap.documents or snap.embeddings is None:
            return []
        return self._dense_search(query, top_k, snap)
    vector_service._dense_search_safe = _dense_search_safe.__get__(vector_service)

    eval_set = build_eval_set()
    print(f'评测集大小: {len(eval_set)} 条')
    print('=' * 60)

    # 维度 1: query 前缀
    print('\n## 维度1: query 前缀')
    for prefix in ['', 'query: ']:
        vector_service.query_prefix = prefix
        m = evaluate(vector_service, eval_set)
        print(f'  prefix={prefix!r:<14} Recall@5={m["recall@5"]:.3f}  MRR@5={m["mrr@5"]:.3f}')

    # 维度 2: 分数阈值
    print('\n## 维度2: min_retrieval_score (strict=True)')
    vector_service.query_prefix = ''  # 复位
    vector_service.strict_threshold = True
    for thr in [0.15, 0.2, 0.25]:
        vector_service.min_retrieval_score = thr
        m = evaluate(vector_service, eval_set)
        print(f'  threshold={thr:<6} Recall@5={m["recall@5"]:.3f}  MRR@5={m["mrr@5"]:.3f}')

    # 维度 3: strict 开关(阈值固定 0.2)
    print('\n## 维度3: strict_threshold (threshold=0.2)')
    vector_service.min_retrieval_score = 0.2
    for strict in [True, False]:
        vector_service.strict_threshold = strict
        m = evaluate(vector_service, eval_set)
        print(f'  strict={strict!s:<6} Recall@5={m["recall@5"]:.3f}  MRR@5={m["mrr@5"]:.3f}')

    print('\n' + '=' * 60)
    print('解读: 前缀 Recall 差异<1% → 维持默认空串;strict=True 若 Recall 不降 → 保留严格。')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
