# app/tools/web_search/router.py
"""网页正文提取 REST API(Tavily extract,走自建代理)。

对外端点:
  POST /extract   提取 URL 正文

注:search / map / crawl / research 能力仍保留在 client.py 作为底层方法,
但不对外暴露为 REST 端点(主动搜索不开放给 Agent,避免不可控)。
"""
from fastapi import APIRouter, HTTPException

from app.config import TAVILY_API_KEY
from app.tools.web_search import client
from app.tools.web_search.schemas import (
    WebExtractRequest,
    WebExtractResponse,
)

router = APIRouter(prefix='/api/tools/web_search', tags=['联网搜索'])


def _ensure_key():
    if not TAVILY_API_KEY:
        raise HTTPException(
            status_code=503,
            detail='Tavily API key 未配置。请在 .env 中设置 TAVILY_API_KEY。',
        )


@router.post('/extract', response_model=WebExtractResponse, summary='提取 URL 正文')
def extract(req: WebExtractRequest):
    _ensure_key()
    try:
        return client.extract(req.urls, req.extract_depth)
    except client.TavilyError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
