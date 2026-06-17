# app/tools/__init__.py
"""自动发现 tools/<name>/tool.py 中定义的 ToolBase 子类并注册到 registry。"""
import importlib
import pkgutil
from pathlib import Path

from app.tools.base import ToolBase
from app.agent.registry import registry

_tools_package_path = Path(__file__).resolve().parent


def discover_and_register():
    """扫描 tools/ 子目录,import 每个 tool.py,注册 ToolBase 子类实例。"""
    for subdir in sorted(_tools_package_path.iterdir()):
        if not subdir.is_dir() or subdir.name.startswith('_'):
            continue
        tool_module_path = f'app.tools.{subdir.name}.tool'
        try:
            mod = importlib.import_module(tool_module_path)
        except ImportError:
            continue  # 子目录没有 tool.py,跳过

        # 在模块中找 ToolBase 子类
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                isinstance(attr, type)
                and issubclass(attr, ToolBase)
                and attr is not ToolBase
                and attr.name  # 有 name 的才是具体工具
            ):
                instance = attr()
                registry.register(instance)


# 首次 import 时自动发现
discover_and_register()
