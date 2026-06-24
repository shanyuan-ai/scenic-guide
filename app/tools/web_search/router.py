# app/tools/web_search/router.py
"""网页正文提取 REST API。

对外端点:
  POST /extract   提取 URL 正文(自研 fetcher)
"""
from fastapi import APIRouter

from app.tools.web_search import fetcher
from app.tools.web_search.schemas import (
    WebExtractRequest,
    WebExtractResponse,
)

router = APIRouter(prefix='/api/tools/web_search', tags=['联网搜索'])


@router.post('/extract', response_model=WebExtractResponse, summary='提取 URL 正文')
async def extract(req: WebExtractRequest):
    return WebExtractResponse(**await fetcher.extract_batch(req.urls))
