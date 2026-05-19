# 景区智能导览 RAG 系统

基于 Django + BGE-M3 的景区知识检索增强生成系统，为游客提供智能问答服务。

## 架构

- **后端**: Django 4.2 + Django REST Framework
- **向量检索**: BGE-M3 (BAAI/bge-m3) 密集检索 + bge-reranker-v2-m3 交叉编码重排
- **LLM**: 豆包 (Volcengine Ark) / OpenAI 兼容接口 / 本地 Ollama
- **分词**: jieba 中文分词 + 景区实体增强
- **向量存储**: NumPy 内存索引（无外部向量数据库依赖）

## 核心流程

```
用户提问 → 热词缓存命中? → 直接返回
         → 景区实体提取 + 查询增强 → BGE-M3 向量召回 (top-20)
         → bge-reranker-v2-m3 精排 (top-5) → 返回结果
         → (可选) LLM 生成回答
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

默认下载到项目 `models/` 目录，也可设置环境变量指定已有模型路径。

### 3. 配置环境变量

复制 `.env.example` 为 `.env`，填入必要的 API Key：

```env
# 豆包 LLM（可选，不使用 chat 功能可不填）
DOUBAO_API_KEY=your_key_here

# 向量检索设备（默认自动检测）
RAG_DEVICE=cpu          # 或 cuda
RAG_USE_FP16=true       # GPU 下启用半精度加速
```

### 4. 初始化数据库

```bash
python manage.py migrate
```

### 5. 导入知识库

```bash
# 使用种子脚本导入灵山胜境知识
python seed_lingshan_knowledge.py

# 或通过 Word 文件导入（访问 /api/rag/upload/）
```

### 6. 启动服务

```bash
python manage.py runserver
```

## API 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/rag/search/?query=xxx&top_k=5` | GET | 知识检索 |
| `/api/rag/index_status/` | GET | 索引状态 |
| `/api/rag/reindex/` | POST | 重建索引 |
| `/api/rag/set_indexed/` | POST | 批量设置索引状态 |
| `/api/rag/chat/` | POST | 智能问答（需 LLM） |
| `/api/rag/upload/` | GET/POST | Word 文件导入 |
| `/api/rag/dashboard/` | GET | 仪表盘数据 |
| `/api/knowledge/` | CRUD | 知识条目管理 |

## 检索质量

压测结果（5 并发，CPU 推理）：

| 指标 | 数值 |
|------|------|
| 成功率 | 100% |
| 平均延迟 | 0.43s |
| 吞吐量 | 11 rps |
| 检索命中率 | 83.3% |
| Top-1 平均分 | 0.919 |

实体类问题命中率 100%，复杂多跳问题 94%，边界场景 79%。

## 项目结构

```
measureapp/
├── models.py            # KnowledgeItem, ConversationLog, DailyStat
├── views.py             # API 视图
├── vector_service.py    # BGE-M3 检索 + reranker 重排
├── llm_utils.py         # 多 LLM 适配（豆包/OpenAI/Ollama）
├── word_importer.py     # Word 文档解析导入
├── serializers.py       # DRF 序列化器
├── urls.py              # 路由配置
├── utils/sentiment.py   # 情感分析
└── forms.py             # 表单定义
```
