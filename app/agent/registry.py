# app/agent/registry.py
"""工具注册中心。收集所有 ToolBase 实例,提供:
- get_all_schemas(): 返回所有 tool schema 列表(供 LLM/前端查询)
- get_tool(name): 按名查找工具实例(供 Agent 执行)
- get_all_routers(): 返回所有工具的 FastAPI Router(供 main.py 挂载)
"""


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, 'ToolBase'] = {}

    def register(self, tool: 'ToolBase'):
        self._tools[tool.name] = tool

    def get_all_schemas(self) -> list[dict]:
        return [tool.get_schema() for tool in self._tools.values()]

    def get_tool(self, name: str) -> 'ToolBase | None':
        return self._tools.get(name)

    def get_all_routers(self):
        """返回所有工具的 FastAPI Router(排除 None)。"""
        routers = []
        for tool in self._tools.values():
            router = tool.get_router()
            if router is not None:
                routers.append(router)
        return routers

    def list_tool_names(self) -> list[str]:
        return sorted(self._tools.keys())


registry = ToolRegistry()
