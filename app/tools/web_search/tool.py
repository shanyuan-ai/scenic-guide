# app/tools/web_search/tool.py
"""联网搜索工具(Tavily)。

action 取值:
  - search:   搜索实时信息(景区公告/天气/新闻/交通),传 query
  - extract:  提取指定 URL 正文,传 urls(列表)

注:map / crawl / research 等能力保留在 client.py 作为底层方法,
但不作为工具 action 暴露给 LLM(景区导览场景用不到)。
"""
from typing import Any

from app.tools.base import ToolBase
from app.tools.web_search import client
from app.tools.web_search.router import router as web_search_router


class WebSearchTool(ToolBase):
    name = 'web_search'
    description = (
        '联网搜索与网页抓取(Tavily)。按 action 选择操作: '
        'search=搜索实时信息(景区公告/天气/新闻/交通); '
        'extract=提取指定 URL 的正文内容(当需要某个网页的全文时使用)。'
    )

    @property
    def input_schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'action': {
                    'type': 'string',
                    'enum': ['search', 'extract'],
                    'default': 'search',
                    'description': '操作类型',
                },
                'query': {'type': 'string', 'description': '搜索关键词(search 必填)'},
                'urls': {
                    'type': 'array',
                    'items': {'type': 'string'},
                    'description': 'URL 列表(extract 必填)',
                },
                'max_results': {'type': 'integer', 'default': 5, 'description': '返回数量上限'},
                'search_depth': {
                    'type': 'string',
                    'default': 'basic',
                    'description': '搜索深度: basic/advanced',
                },
            },
            'required': ['action'],
        }

    async def execute(self, params: dict) -> Any:
        action = params.get('action', 'search')
        try:
            if action == 'search':
                return client.search(
                    query=params.get('query', ''),
                    max_results=params.get('max_results', 5),
                    search_depth=params.get('search_depth', 'basic'),
                )
            if action == 'extract':
                return client.extract(urls=params.get('urls', []))
            return {'error': f'未知 action: {action}'}
        except client.TavilyError as exc:
            return {'error': str(exc)}

    def get_router(self):
        return web_search_router
