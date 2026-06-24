# app/tools/web_search/tool.py
"""网页正文提取工具(Tavily extract)。

仅做确定性的「给定 URL → 提取正文」一件事。主动搜索能力不暴露给 Agent,
避免 Agent 不可控地乱搜;数据库中已存的链接由 Agent 通过本工具解析正文。

注:search / map / crawl / research 等底层能力仍保留在 client.py,
供内部/未来按需调用,但不作为工具 action 暴露。
"""
from typing import Any

from app.tools.base import ToolBase
from app.tools.web_search import client
from app.tools.web_search.router import router as web_search_router


class WebSearchTool(ToolBase):
    name = 'web_search'
    description = '提取指定网页 URL 的正文内容(Tavily extract)。当需要某个已知链接的全文/正文时使用。'

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
                'extract_depth': {
                    'type': 'string',
                    'default': 'basic',
                    'description': '提取深度: basic/advanced',
                },
            },
            'required': ['urls'],
        }

    async def execute(self, params: dict) -> Any:
        try:
            return client.extract(
                urls=params.get('urls', []),
                extract_depth=params.get('extract_depth', 'basic'),
            )
        except client.TavilyError as exc:
            return {'error': str(exc)}

    def get_router(self):
        return web_search_router
