# app/tools/rag/tool.py
"""RAG 知识检索工具的 ToolBase 定义。

提供:
- tool schema (供 LLM function calling / 前端 /api/tools 查询)
- execute 函数 (供 Agent 调度层调用)
- FastAPI Router (供前端直接 REST 调用,在 router.py 中定义)
"""
from typing import Any

from app.tools.base import ToolBase
from app.tools.rag.vector_service import vector_service
from app.tools.rag.router import router as rag_router


class RagSearchTool(ToolBase):
    name = 'rag_search'
    description = '搜索灵山胜境景区知识库,返回相关景点介绍、历史典故、常见问题、路线推荐等信息'

    @property
    def input_schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'query': {
                    'type': 'string',
                    'description': '检索问题,如"灵山大佛的手势含义"、"门票价格"、"怎么去"',
                },
                'top_k': {
                    'type': 'integer',
                    'default': 5,
                    'description': '返回结果数(1-50)',
                },
            },
            'required': ['query'],
        }

    async def execute(self, params: dict) -> Any:
        query = params.get('query', '')
        top_k = params.get('top_k', 5)
        results = vector_service.search(query, top_k=top_k)
        return {
            'query': query,
            'top_k': top_k,
            'results': results,
        }

    def get_router(self):
        return rag_router
