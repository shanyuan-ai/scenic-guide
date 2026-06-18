# app/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# 本项目使用本地模型权重(由 download_model.py 下载到 models/)。
# 默认禁止 transformers 联网自动下载,避免无网络或无本地模型时启动卡死。
# 模型加载失败会自动降级为关键词检索,服务仍可正常启动。
# 如需从 HuggingFace 在线加载远程模型,设 RAG_ALLOW_DOWNLOAD=true。
if os.getenv('RAG_ALLOW_DOWNLOAD', 'false').lower() not in ('1', 'true', 'yes', 'on'):
    os.environ.setdefault('TRANSFORMERS_OFFLINE', '1')
    os.environ.setdefault('HF_HUB_OFFLINE', '1')

# ---- 数据库 ----
DB_URL = os.getenv('DB_URL', f'sqlite:///{BASE_DIR / "db.sqlite3"}')

# ---- 文件上传(反馈图片等) ----
UPLOAD_DIR = BASE_DIR / 'uploads'

# ---- 联网搜索(Tavily 风格,走自建代理) ----
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY', '')
TAVILY_BASE_URL = os.getenv('TAVILY_BASE_URL', 'https://tavily.ivanli.cc/api/tavily')

# ---- LLM(报单智能整合等后台任务) ----
LLM_API_KEY = os.getenv('LLM_API_KEY', '')
LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
LLM_MODEL = os.getenv('LLM_MODEL', 'qwen3.5-flash')

# ---- RAG 模型 ----
RAG_DEVICE = os.getenv('RAG_DEVICE', 'auto')
RAG_USE_FP16 = os.getenv('RAG_USE_FP16', 'true').lower() in ('1', 'true', 'yes', 'on')
RAG_BATCH_SIZE = int(os.getenv('RAG_BATCH_SIZE', '8'))
RAG_MAX_LENGTH = int(os.getenv('RAG_MAX_LENGTH', '8192'))
RAG_RETRIEVAL_TOP_K = int(os.getenv('RAG_RETRIEVAL_TOP_K', '20'))
RAG_RETRIEVAL_MIN_SCORE = float(os.getenv('RAG_RETRIEVAL_MIN_SCORE', '0.2'))
RAG_POOLING = (os.getenv('RAG_POOLING', 'cls') or 'cls').strip().lower()
RAG_RERANKER_MAX_LENGTH = int(os.getenv('RAG_RERANKER_MAX_LENGTH', '512'))
RAG_PREWARM_ON_STARTUP = os.getenv('RAG_PREWARM_ON_STARTUP', 'true').lower() in ('1', 'true', 'yes', 'on')
RAG_ENABLE_RERANKER = os.getenv('RAG_ENABLE_RERANKER', 'false').lower() in ('1', 'true', 'yes', 'on')


def resolve_model_name(env_var: str, local_dir_name: str) -> str:
    """优先读环境变量,其次检查本地 models/ 目录,最后返回 HuggingFace repo ID."""
    configured = os.getenv(env_var)
    if configured:
        return configured
    local_path = BASE_DIR / 'models' / local_dir_name
    if local_path.exists():
        return str(local_path)
    # 返回默认 HuggingFace repo
    defaults = {
        'RAG_EMBEDDING_MODEL': 'BAAI/bge-m3',
        'RAG_RERANKER_MODEL': 'BAAI/bge-reranker-v2-m3',
    }
    return defaults.get(env_var, '')


RAG_EMBEDDING_MODEL = resolve_model_name('RAG_EMBEDDING_MODEL', 'bge-m3')
RAG_RERANKER_MODEL = resolve_model_name('RAG_RERANKER_MODEL', 'bge-reranker-v2-m3')
