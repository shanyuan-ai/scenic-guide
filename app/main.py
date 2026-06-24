# app/main.py
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.common.db import init_db, migrate_feedback_table
from app.tools import registry  # 自动发现+注册所有工具
from app.tools.rag.vector_service import vector_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时初始化数据库并执行迁移。"""
    import sys
    print("DEBUG_STARTUP_EXECUTABLE:", sys.executable)
    print("DEBUG_STARTUP_ARGV:", sys.argv)
    init_db()
    migrate_feedback_table()
    if config.RAG_PREWARM_ON_STARTUP:
        try:
            vector_service.ensure_index()
        except Exception as exc:
            print(f"DEBUG_RAG_PREWARM_FAILED: {exc}")
    # 预热 web_search fetcher 连接池(httpx AsyncClient 单例)。
    from app.tools.web_search import fetcher
    fetcher.get_client()
    yield
    # 回收连接池。
    await fetcher.close_client()


app = FastAPI(
    title='景区智能导览工具平台',
    description='多工具 REST API 服务(RAG检索/用户反馈/应急系统/联网搜索)',
    version='3.0.0',
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

# ---- 挂载所有工具的 REST 路由 ----
for router in registry.get_all_routers():
    app.include_router(router)

# ---- 全局端点 ----


@app.get('/', tags=['健康检查'])
def root():
    return {
        'service': '景区智能导览工具平台',
        'status': 'running',
        'tools': registry.list_tool_names(),
        'docs': '/docs',
    }


@app.get('/api/tools', tags=['工具查询'])
def list_tools():
    """列出所有已注册工具及其 schema(供前端/LLM 查看)。"""
    return registry.get_all_schemas()


@app.post('/api/system/restart', tags=['系统管理'])
def restart_server():
    """重启后端服务。"""
    import os
    import sys
    import threading
    import time
    from pathlib import Path

    # 1. 如果检测到 uvicorn 的 reload 参数，我们直接 touch app/main.py 即可，不需要结束当前进程
    is_reload = any(arg in sys.argv for arg in ["--reload", "--reload-dir"])
    if is_reload:
        try:
            Path(__file__).touch()
            return {'status': 'reloaded', 'message': '检测到热重载模式，已成功触发服务热重载。'}
        except Exception as e:
            return {'status': 'error', 'message': f'触发热重载失败: {str(e)}'}

    # 2. 如果是非热重载模式（生产模式），起一个后台线程，在响应返回后执行真正的独立进程重启
    def reload_backend():
        time.sleep(0.5)
        try:
            import subprocess
            # 如果 sys.argv[0] 是以 .exe 结尾的二进制（如 uvicorn.exe）
            if sys.argv[0].lower().endswith(".exe"):
                cmd = sys.argv
            else:
                cmd = [sys.executable] + sys.argv

            # 将命令行列表安全地合并为字符串（处理包含空格的参数）
            cmd_str = " ".join(f'"{arg}"' if ' ' in arg else arg for arg in cmd)

            # 使用外部 shell 命令进行延时拉起，确保当前进程有足够时间退出并彻底释放 8000 端口
            if os.name == 'nt':
                # Windows 使用 ping 模拟延迟 1.5 秒再拉起新进程（timeout 命令在无 TTY 分离进程下会报错）
                shell_cmd = f"ping 127.0.0.1 -n 3 > nul & {cmd_str}"
                subprocess.Popen(
                    ["cmd.exe", "/c", shell_cmd],
                    creationflags=0x00000008 | 0x00000200, # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
                    close_fds=True
                )
            else:
                # Unix 使用 sleep 延时 1.5 秒再拉起新进程
                shell_cmd = f"sleep 1.5 && {cmd_str}"
                subprocess.Popen(
                    ["sh", "-c", shell_cmd],
                    start_new_session=True,
                    close_fds=True
                )
        except Exception:
            pass
        finally:
            # 退出当前进程，释放端口
            os._exit(0)

    threading.Thread(target=reload_backend).start()
    return {'status': 'restarting', 'message': '后端服务正在独立重启中，约 2 秒后连接恢复...'}
