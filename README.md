# 景区智能导览工具平台

基于 FastAPI 的**多工具 REST 平台**，为景区（灵山胜境）数字人原型提供知识检索、用户反馈、应急上报、联网搜索等工具后端。核心是 BGE-M3 向量检索服务。

从早期的 Django 单体 RAG 服务演进而来：先是精简为纯 RAG 检索，再重构为插件式的「工具平台 + Agent 调度」架构。

## 架构

- **后端**: FastAPI + Uvicorn + SQLAlchemy + SQLite
- **工具平台**: 插件式自动发现（`tools/<name>/tool.py` 定义 `ToolBase`，自动注册 schema + REST 路由）
- **向量检索**: BGE-M3 (BAAI/bge-m3) 密集检索（NumPy 内存索引，无外部向量数据库）
- **分词**: jieba 中文分词 + 景区实体增强
- **LLM**: OpenAI 兼容客户端（qwen3.5-flash，仅用于 feedback 报单智能整合等后台任务，不参与用户对话）

### 内置工具

| 工具 | 说明 |
|------|------|
| `rag_search` | 景区知识库向量检索（BGE-M3 + 关键词兜底 + 热词缓存） |
| `feedback` | 游客反馈提交/查询/更新 + LLM 智能整合（去重分组、优先级升级） |
| `emergency` | 应急事件上报与响应流程追踪 |
| `web_search` | 网页正文提取（自研 fetcher，httpx + trafilatura） |

## RAG 检索核心流程

```
用户提问 → 热词缓存命中? → 直接返回
         → 景区实体提取 + 查询增强 → BGE-M3 向量召回 (top-20)
         → 严格分数门槛过滤 → 返回 top_k 结果
         → (召回为空或模型不可用时) jieba 关键词兜底检索
```

### 并发与性能设计

- **并发安全**：query 编码无锁（`torch.inference_mode` 下只读前向，并发安全）；「检查脏 → 重建 → 替换」在临界区内完成，末尾用单一不可变快照 `_IndexSnapshot` 原子替换，杜绝读到半截状态。
- **索引持久化**：embeddings 落盘为 `cache/rag_index_embeddings.npy`，按内容指纹（sha1）校验。冷启动从全量编码（~6s）降到缓存加载（~0.02s）。
- **增删改自动失效**：知识条目 CRUD 会标记索引为脏，下次检索前按指纹比对自动重建。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 下载模型

```bash
python download_model.py
```

默认下载到项目 `models/` 目录（国内走 ModelScope 镜像）。仅需 `bge-m3` 一个模型。

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，按需调整（均可省略，用默认值即可运行）：

```env
RAG_DEVICE=auto          # auto | cpu | cuda
```

### 4. 导入知识库

```bash
# 内置种子数据（25 条灵山胜境知识）
python seed_lingshan_knowledge.py

# 或从 data/ 下的 Word 文件导入
python import_knowledge.py
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动后访问交互式文档: <http://localhost:8000/docs>，工具 schema 查询: <http://localhost:8000/api/tools>

## API 接口

### RAG 检索

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/tools/rag/search?query=xxx&top_k=5` | GET | 知识检索 |
| `/api/tools/rag/index_status` | GET | 索引状态 |
| `/api/tools/rag/reindex` | POST | 重建索引（触发持久化落盘） |
| `/api/tools/rag/set_indexed` | POST | 批量设置索引状态 |

**检索示例:**

```bash
curl "http://localhost:8000/api/tools/rag/search?query=门票多少钱&top_k=3"
```

```json
{
  "query": "门票多少钱",
  "top_k": 3,
  "results": [
    {
      "id": 18,
      "title": "灵山胜境门票与优惠政策（参考汇总）",
      "content": "...",
      "category": "faq",
      "score": 0.95,
      "source_type": "bge_m3",
      "retrieval_score": 0.82
    }
  ]
}
```

> `source_type` 取值：`cache`（热词命中）/ `bge_m3`（向量检索）/ `keyword`（兜底）。

### 知识库管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/tools/rag/knowledge` | GET | 列表（支持 `category`、`is_indexed`、`skip`、`limit` 过滤） |
| `/api/tools/rag/knowledge/{id}` | GET | 详情 |
| `/api/tools/rag/knowledge` | POST | 创建 |
| `/api/tools/rag/knowledge/{id}` | PUT | 更新 |
| `/api/tools/rag/knowledge/{id}` | DELETE | 删除 |

**创建示例:**

```bash
curl -X POST http://localhost:8000/api/tools/rag/knowledge \
  -H "Content-Type: application/json" \
  -d '{"title":"测试条目","content":"内容","category":"faq","is_indexed":true}'
```

> 增删改会自动标记索引为脏，下次检索前自动重建并刷新持久化缓存。

## 项目结构

```
app/
├── main.py                # FastAPI 入口（lifespan 初始化 DB + 预热索引、CORS、挂载路由）
├── config.py              # 环境变量配置
├── common/
│   ├── db.py              # SQLAlchemy engine + session + 迁移
│   └── base_model.py      # ORM Base
├── agent/
│   ├── registry.py        # 工具注册中心（schema 查询 / 路由收集）
│   └── llm.py             # OpenAI 兼容 LLM 客户端（后台任务用）
└── tools/                 # 自动发现：扫描子目录注册 ToolBase
    ├── base.py            # 工具抽象基类（schema + execute + router）
    ├── rag/
    │   ├── vector_service.py  # 核心：BGE-M3 检索 + 持久化 + 并发快照
    │   ├── router.py          # search / index_status / reindex / knowledge CRUD
    │   └── eval_retrieval.py  # 检索质量评测脚本（非生产代码）
    ├── feedback/          # 用户反馈 + LLM 智能整合
    ├── emergency/         # 应急事件
    └── web_search/        # 网页正文提取（自研 fetcher）
```

## 检索质量与性能参考

基于 25 条灵山胜境知识、CPU 推理的实测（统一口径基准）：

**质量**（20 条真实游客口吻查询，口语化、不含标题原词）：

| 指标 | 结果 |
|------|------|
| Recall@1 | 85%（17/20 dense top-1 直接命中） |
| Recall@5 | 90% |
| MRR | 0.875 |

**速度**：

| 指标 | 结果 |
|------|------|
| 稳态单次检索 p50 | ~8 ms |
| 5 并发吞吐 | 130–174 rps |
| 冷启动（无缓存） | ~6 s（全量编码） |
| 冷启动（有缓存） | ~0.02 s（指纹校验加载） |

> 可运行 `python -m app.tools.rag.eval_retrieval` 复现检索质量评测。

## 集成维护提醒

这个仓库当前已被数字人原型作为真实工具后端接入。

如果要调整工具接口、字段或响应形状，请先看：

- [docs/digital-human-integration-notes.md](docs/digital-human-integration-notes.md)

## 配置说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DB_URL` | `sqlite:///db.sqlite3` | 数据库连接 |
| `RAG_DEVICE` | `auto` | 推理设备（auto/cpu/cuda） |
| `RAG_USE_FP16` | `true` | GPU 半精度 |
| `RAG_BATCH_SIZE` | `8` | 编码批大小 |
| `RAG_MAX_LENGTH` | `8192` | 编码最大 token |
| `RAG_RETRIEVAL_TOP_K` | `20` | 召回候选数 |
| `RAG_RETRIEVAL_MIN_SCORE` | `0.2` | 最低召回分 |
| `RAG_POOLING` | `cls` | 池化方式（cls/mean） |
| `RAG_EMBEDDING_MODEL` | 自动检测 | 嵌入模型路径或 repo |
| `RAG_QUERY_PREFIX` | （空） | query 前缀（BGE-M3 实测无需，保留兼容） |
| `RAG_STRICT_THRESHOLD` | `true` | 严格分数门槛，召回为空不硬塞结果 |
| `RAG_TORCH_NUM_THREADS` | `min(核数,4)` | CPU 推理线程数 |
| `RAG_INT8_QUANTIZE` | `false` | CPU 下 INT8 动态量化（opt-in，需 eval 验证） |
| `RAG_CACHE_DIR` | `cache/` | 索引持久化目录 |
| `RAG_CACHE_DISABLED` | `false` | 关闭索引持久化 |
| `LLM_API_KEY` | （空） | feedback 智能整合用，留空则降级 |
