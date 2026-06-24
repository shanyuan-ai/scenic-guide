# app/tools/web_search/schemas.py
from typing import Any, Optional

from pydantic import BaseModel, Field


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
