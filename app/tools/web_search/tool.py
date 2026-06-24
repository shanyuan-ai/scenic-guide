# app/tools/web_search/tool.py
"""网页正文提取工具。

给定 URL 列表,提取每个页面的正文(自研 fetcher:httpx + trafilatura,无外部 API 依赖)。
主动搜索能力不暴露给 Agent,避免不可控;数据库中已存的链接由 Agent 通过本工具解析正文。
"""
from typing import Any

from app.tools.base import ToolBase
from app.tools.web_search import fetcher
from app.tools.web_search.router import router as web_search_router


class WebSearchTool(ToolBase):
    name = 'web_search'
    description = '提取指定网页 URL 的正文内容。当需要某个已知链接的全文/正文时使用。'

    @property
    def input_schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'urls': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': '待提取正文的 URL 列表',
                },
            },
            'required': ['urls'],
        }

    async def execute(self, params: dict) -> Any:
        return await fetcher.extract_batch(params.get('urls', []))

    def get_router(self):
        return web_search_router
