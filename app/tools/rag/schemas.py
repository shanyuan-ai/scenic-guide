# app/tools/rag/schemas.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    id: Optional[int] = None
    content: str
    title: str
    category: str
    score: float
    source_type: str
    retrieval_score: Optional[float] = None


class SearchResponse(BaseModel):
    query: str
    top_k: int
    results: list[SearchResult]


class KnowledgeItemBase(BaseModel):
    title: str = Field(..., max_length=200)
    content: str
    category: str = 'faq'


class KnowledgeItemCreate(KnowledgeItemBase):
    is_indexed: bool = False


class KnowledgeItemUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    content: Optional[str] = None
    category: Optional[str] = None
    is_indexed: Optional[bool] = None


class KnowledgeItemResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    is_indexed: bool
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IndexStatusResponse(BaseModel):
    total_items: int
    indexed_items: int
    index_ready: bool
    model_error: Optional[str] = None


class SetIndexedRequest(BaseModel):
    ids: list[int]
    is_indexed: bool = True


class SetIndexedResponse(BaseModel):
    updated: int
