# app/tools/web_search/schemas.py
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---- search ----
class WebSearchRequest(BaseModel):
    query: str = Field(..., description='搜索关键词')
    max_results: int = Field(5, ge=1, le=20, description='返回结果数')
    search_depth: str = Field('basic', description='搜索深度: basic/advanced')
    topic: str = Field('general', description='分类: general/news')
    include_answer: bool = Field(False, description='是否生成摘要答案')


class WebSearchResult(BaseModel):
    title: str = ''
    url: str = ''
    content: str = ''
    score: Optional[float] = None


class WebSearchResponse(BaseModel):
    query: str
    answer: Optional[str] = None
    results: list[WebSearchResult] = []
    response_time: Optional[float] = None


# ---- extract ----
class WebExtractRequest(BaseModel):
    urls: list[str] = Field(..., description='待提取正文的 URL 列表')
    extract_depth: str = Field('basic', description='提取深度: basic/advanced')


class WebExtractResult(BaseModel):
    url: Optional[str] = ''
    title: Optional[str] = ''
    raw_content: Optional[str] = ''


class WebExtractResponse(BaseModel):
    results: list[WebExtractResult] = []
    failed_results: list[Any] = []
    response_time: Optional[float] = None
