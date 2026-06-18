# 景区智能导览 RAG 检索服务

基于 FastAPI + BGE-M3 的景区知识检索服务，为游客提供智能问答的知识检索能力。
已精简为**纯 RAG 检索**（移除了 LLM 生成、对话记录、仪表盘、情感分析等附属功能）。

## 架构

- **后端**: FastAPI + Uvicorn + SQLAlchemy + SQLite
- **向量检索**: BGE-M3 (BAAI/bge-m3) 密集检索 + bge-reranker-v2-m3 交叉编码重排
- **分词**: jieba 中文分词 + 景区实体增强
- **向量存储**: NumPy 内存索引（无外部向量数据库依赖）

## 核心流程

```
用户提问 → 热词缓存命中? → 直接返回
         → 景区实体提取 + 查询增强 → BGE-M3 向量召回 (top-20)
         → bge-reranker-v2-m3 精排 (top-5) → 返回检索结果
         → (模型不可用时) jieba 关键词兜底检索
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 下载模型

```bash
python download_model.py
```

默认下载到项目 `models/` 目录（国内会走 hf-mirror 镜像）。

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，按需调整：

```env
RAG_DEVICE=auto          # auto | cpu | cuda
RAG_USE_FP16=true        # GPU 下启用半精度加速
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

启动后访问交互式文档: <http://localhost:8000/docs>

## API 接口

### RAG 检索

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/rag/search?query=xxx&top_k=5` | GET | 知识检索 |
| `/api/rag/index_status` | GET | 索引状态 |
| `/api/rag/reindex` | POST | 重建索引 |
| `/api/rag/set_indexed` | POST | 批量设置索引状态 |

**检索示例:**

```bash
curl "http://localhost:8000/api/rag/search?query=门票多少钱&top_k=3"
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
      "source_type": "bge_m3_reranker",
      "retrieval_score": 0.82,
      "rerank_score": 0.95
    }
  ]
}
```

### 知识库管理

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/knowledge` | GET | 列表（支持 `category`、`is_indexed`、`skip`、`limit` 过滤） |
| `/api/knowledge/{id}` | GET | 详情 |
| `/api/knowledge` | POST | 创建 |
| `/api/knowledge/{id}` | PUT | 更新 |
| `/api/knowledge/{id}` | DELETE | 删除 |

**创建示例:**

```bash
curl -X POST http://localhost:8000/api/knowledge \
  -H "Content-Type: application/json" \
  -d '{"title":"测试条目","content":"内容","category":"faq","is_indexed":true}'
```

> 增删改后会自动标记索引为"脏"，下次检索前自动重建。也可手动调用 `/api/rag/reindex`。

## 项目结构

```
app/
├── main.py                # FastAPI 入口(lifespan 预加载索引、CORS、路由挂载)
├── config.py              # 环境变量配置(替代 Django settings)
├── database.py            # SQLAlchemy engine + session
├── models.py              # KnowledgeItem 模型(兼容旧 db.sqlite3 表名)
├── schemas.py             # Pydantic 请求/响应模型
├── vector_service.py      # 核心:BGE-M3 检索 + reranker 重排 + 关键词兜底
└── routers/
    ├── rag.py             # search / index_status / reindex / set_indexed
    └── knowledge.py       # 知识条目 CRUD
```

## 检索质量参考

压测结果（5 并发，CPU 推理）：成功率 100%，平均延迟 0.43s，吞吐量 11 rps，
检索命中率 83.3%，Top-1 平均分 0.919。

## 集成维护提醒

这个仓库当前已经被数字人原型作为真实工具后端接入。

如果要调整工具接口、字段或响应形状，请先看：

- [docs/digital-human-integration-notes.md](docs/digital-human-integration-notes.md)

## 配置说明

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `DB_URL` | `sqlite:///db.sqlite3` | 数据库连接 |
| `RAG_DEVICE` | `auto` | 推理设备 |
| `RAG_USE_FP16` | `true` | GPU 半精度 |
| `RAG_BATCH_SIZE` | `8` | 编码批大小 |
| `RAG_RETRIEVAL_TOP_K` | `20` | 召回候选数 |
| `RAG_RETRIEVAL_MIN_SCORE` | `0.2` | 最低召回分 |
| `RAG_POOLING` | `cls` | 池化方式(cls/mean) |
| `RAG_EMBEDDING_MODEL` | 自动检测 | 嵌入模型路径或 repo |
| `RAG_RERANKER_MODEL` | 自动检测 | 重排模型路径或 repo |
