# app/tools/base.py
"""工具抽象基类。每个工具模块在 tools/<name>/tool.py 中定义 ToolBase 子类,
通过 registry 自动发现并注册。

每个工具提供:
- tool schema (JSON Schema,供 LLM function calling / 前端查询)
- execute 函数 (供 Agent 调度层调用)
- FastAPI Router (供前端直接 REST 调用)
"""
from abc import ABC, abstractmethod
from typing import Any

from fastapi import APIRouter


class ToolBase(ABC):
    name: str = ''
    description: str = ''

    def get_schema(self) -> dict:
        """返回 OpenAI function calling 格式的 tool schema。
        子类可直接定义 self.input_schema 或重写此方法。"""
        return {
            'name': self.name,
            'description': self.description,
            'parameters': self.input_schema,
        }

    @property
    def input_schema(self) -> dict:
        """工具输入参数的 JSON Schema。子类应定义此属性。"""
        return {
            'type': 'object',
            'properties': {},
            'required': [],
        }

    @abstractmethod
    async def execute(self, params: dict) -> Any:
        """执行工具。params 为 JSON Schema 验证后的参数 dict。"""
        ...

    def get_router(self) -> APIRouter | None:
        """返回工具的 REST API Router(可选,有些工具可能不需要)。"""
        return None
