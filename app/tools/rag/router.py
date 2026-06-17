# app/tools/rag/router.py
"""RAG 工具的 REST API 路由。包含检索接口和知识库 CRUD 管理。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.common.db import get_session
from app.tools.rag.models import KnowledgeItem
from app.tools.rag.schemas import (
    SearchResponse, SearchResult,
    IndexStatusResponse,
    SetIndexedRequest, SetIndexedResponse,
    KnowledgeItemCreate, KnowledgeItemUpdate, KnowledgeItemResponse,
)
from app.tools.rag.vector_service import vector_service

router = APIRouter(prefix='/api/tools/rag', tags=['RAG 知识检索'])


# ---- 检索接口 ----

@router.get('/search', response_model=SearchResponse, summary='知识检索')
def search(
    query: str = Query(..., description='检索问题'),
    top_k: int = Query(5, ge=1, le=50, description='返回结果数'),
):
    results = vector_service.search(query, top_k=top_k)
    return SearchResponse(
        query=query,
        top_k=top_k,
        results=[SearchResult(**r) for r in results],
    )


@router.get('/index_status', response_model=IndexStatusResponse, summary='索引状态')
def index_status():
    return IndexStatusResponse(**vector_service.index_status())


@router.post('/reindex', summary='重建索引')
def reindex():
    count = vector_service.sync_all_knowledge()
    return {'message': f'索引重建完成，共 {count} 条文档', 'indexed_count': count}


@router.post('/set_indexed', response_model=SetIndexedResponse, summary='批量设置索引状态')
def set_indexed(req: SetIndexedRequest):
    from app.common.db import SessionLocal
    session = SessionLocal()
    try:
        updated = (
            session.query(KnowledgeItem)
            .filter(KnowledgeItem.id.in_(req.ids))
            .update({KnowledgeItem.is_indexed: req.is_indexed}, synchronize_session='fetch')
        )
        session.commit()
    finally:
        session.close()
    vector_service.mark_dirty()
    return SetIndexedResponse(updated=updated)


# ---- 知识库 CRUD ----

@router.get('/knowledge', response_model=list[KnowledgeItemResponse], summary='知识条目列表')
def list_items(
    skip: int = 0, limit: int = 100,
    category: str | None = None, is_indexed: bool | None = None,
    session: Session = Depends(get_session),
):
    q = session.query(KnowledgeItem).order_by(KnowledgeItem.created_at.desc())
    if category is not None:
        q = q.filter_by(category=category)
    if is_indexed is not None:
        q = q.filter_by(is_indexed=is_indexed)
    return q.offset(skip).limit(limit).all()


@router.get('/knowledge/{item_id}', response_model=KnowledgeItemResponse, summary='知识条目详情')
def get_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(KnowledgeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='知识条目不存在')
    return item


@router.post('/knowledge', response_model=KnowledgeItemResponse, status_code=201, summary='创建知识条目')
def create_item(data: KnowledgeItemCreate, session: Session = Depends(get_session)):
    item = KnowledgeItem(**data.model_dump())
    session.add(item)
    session.commit()
    session.refresh(item)
    vector_service.mark_dirty()
    return item


@router.put('/knowledge/{item_id}', response_model=KnowledgeItemResponse, summary='更新知识条目')
def update_item(item_id: int, data: KnowledgeItemUpdate, session: Session = Depends(get_session)):
    item = session.get(KnowledgeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='知识条目不存在')
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(item, key, value)
    session.commit()
    session.refresh(item)
    vector_service.mark_dirty()
    return item


@router.delete('/knowledge/{item_id}', summary='删除知识条目')
def delete_item(item_id: int, session: Session = Depends(get_session)):
    item = session.get(KnowledgeItem, item_id)
    if not item:
        raise HTTPException(status_code=404, detail='知识条目不存在')
    session.delete(item)
    session.commit()
    vector_service.mark_dirty()
    return {'message': '已删除', 'id': item_id}
