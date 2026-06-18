# 反馈系统智能化 —— 后端变更说明

> 给前端同学的协作说明。本次后端对**用户反馈(报单)系统**做了智能化改造，接口字段和新增了端点。
> 涉及工具：`feedback`（景区游客投诉/建议/表扬/求助）。

---

## 一句话概括

反馈报单现在能**自动合并重复**、**动态调整优先级**，就像 GitHub Issue 那样。
重复的报单会被后台 LLM 识别出来，合并到最早的报单上，被合并的进"回收站"不在主列表出现；
同一个问题被反复上报越多，优先级自动越高（P3 → P2 → P1）。

---

## 后端做了什么

### 1. 字段重命名：`severity` → `priority`

旧的严重度 `severity`(`low/medium/high/critical`) 改成了**优先级** `priority`，取值：

| 值 | 含义 | 场景 |
|----|------|------|
| `P1` | 紧急 | 重复上报 ≥ 8 次自动升级 |
| `P2` | 高 | 重复上报 ≥ 4 次自动升级 |
| `P3` | 中 | **新反馈默认值**；重复上报 ≥ 2 次 |
| `P4` | 低 | 手动降级时使用 |

> ⚠️ **破坏性变更**：所有用到 `severity` 的地方都要改成 `priority`。旧库会在启动时自动检测并重建（数据为空，无损失）。

### 2. 新增字段（`feedback_items` 表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `priority` | String | 优先级 P1-P4（替代 severity） |
| `keywords` | Text(JSON) | 关键词标签数组。**提交时可带多个**，但**评估后收敛为单个**（LLM 从候选中选出最核心的原因，如"垃圾桶少"而非空泛的"卫生差"）。不带则后台 LLM 自动提取单个 |
| `evaluated` | Boolean | 是否已被 LLM 整合评估过（`false`=待处理） |
| `group_id` | String | 重复分组标识（组内最小 id），`null`=独立报单 |
| `duplicate_count` | Integer | 所属重复组的上报次数，单条=1 |
| `group_summary` | Text | LLM 为该组生成的综合摘要 |
| `merged_into_id` | Integer | 被合并到的原始报单 id，`null`=未被合并 |

### 3. 新增「回收站」表 `feedback_recycle_bin`

被合并/关闭的报单**不再留在主表**，迁移到独立的回收站表。字段与主表类似，额外有：
- `original_id`：迁移前的原报单 id
- `merged_into_id`：合并到哪条
- `merge_reason`：合并原因（如 "LLM判定与#3重复"）
- `archived_at`：归档时间

### 4. 智能整合机制（后台 LLM 自动跑）

新报单提交后会**自动触发**后台整合（异步，不阻塞响应）。整合逻辑：

1. **关键词原子化**：复合关键词（如 `"垃圾桶少;卫生差"`）拆成独立原子
2. **LLM 两轮匹配**（匹配阶段用全量关键词保召回）：
   - 第 1 轮：把已评估报单的关键词发给 LLM，判断新报单关键词是否与已有问题相似
   - 第 2 轮：LLM 回传匹配关键词 → 系统查对应报单详情 → LLM 评估是否真重复
3. **合并决策**：
   - **重复** → 被合并报单进回收站，原始报单得到描述补充 + `duplicate_count+1` + 按数量升优先级（锚点关键词保持单标签，不累加）
   - **新问题** → 标记 `evaluated=true`，成为新的"锚点"供未来匹配
4. **评估后单关键词收敛**：成为锚点时，若报单提交时带了多个关键词，LLM 从中选出**最核心的一个**（优先具体可执行的原因，如"垃圾桶少"，避开"卫生差"这类空泛描述）落库
5. **LLM 不可用时**自动降级为规则版（按 `景点+类型` 签名分组，关键词取第一个原子，不调 LLM）

> 集成的是 qwen3.5-flash（DashScope，OpenAI 兼容接口）。已关闭 thinking 模式，单次调用 < 1s。

---

## 接口变更

### 基础路径：`/api/tools/feedback`

### 改动的端点

#### `GET /api/tools/feedback`（列表）
- 筛选参数 `severity` → **`priority`**（值 `P1/P2/P3/P4`）
- **自动排除已合并的报单**（`status='merged'` 不出现在列表）

#### `POST /api/tools/feedback`（提交）
请求体新增可选字段：
```json
{
  "type": "complaint",
  "priority": "P3",
  "scenic_spot": "灵山大佛",
  "description": "景区垃圾桶太少了，地上都是垃圾",
  "keywords": ["垃圾桶少", "卫生差"],
  "contact_info": "13800138000"
}
```
- `priority` 默认 `P3`（不再是 `severity`）
- `keywords` 可选，不传则后台 LLM 自动提取
- 提交后**自动触发后台整合**（异步）

#### `PUT /api/tools/feedback/{id}`（更新）
- 字段 `severity` → `priority`
- 支持更新 `keywords`

#### `GET /api/tools/feedback/{id}`（详情）
响应体新增字段（见上方字段表）：`priority`、`keywords`、`evaluated`、`group_id`、`duplicate_count`、`group_summary`、`merged_into_id`

### 新增端点

#### `POST /api/tools/feedback/integrate` —— 手动触发整合
管理员/外部调度器手动跑一次报单整合。返回统计：
```json
{
  "evaluated_count": 3,
  "merged_count": 2,
  "new_groups": 1,
  "priority_upgrades": 1,
  "method": "llm",
  "error": null
}
```
- `method`：`llm`（模型）/ `rule`（降级规则版）
- `error`：LLM 不可用时的降级说明

#### `GET /api/tools/feedback/recycle-bin` —— 回收站列表
查看被合并/关闭的报单。返回 `RecycleBinResponse` 列表，含 `original_id`、`merged_into_id`、`merge_reason`、`archived_at`。

### Tool schema（`/api/tools/feedback` 的 tool 定义）
- `action` 枚举新增 `integrate`
- 参数 `severity` → `priority`
- 新增可选参数 `keywords`

---

## 环境变量

`.env` 新增（前端同学不用管，后端已配好）：
```
LLM_API_KEY=...
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen3.5-flash
```

---

## 前端需要关注的点

1. **所有 `severity` 改成 `priority`**（值从 `low/medium/high/critical` → `P1/P2/P3/P4`）
2. **列表接口已自动过滤 merged**，不用前端再筛
3. **提交时可带 `keywords`**（可多个，用户手填或前端做标签选择都行）；不带也能用——后台会自动提取。注意：**评估后只保留单个关键词**（LLM 选最核心的原因），所以列表里已评估报单的 `keywords` 数组长度恒为 1（待评估的可能 >1）
4. **想展示"重复热度"**：用 `duplicate_count` 字段（>1 说明是热点问题）
5. **想展示分组**：用 `group_id` 聚合，或用 `group_summary` 展示 LLM 生成的综合描述
6. **回收站**：单独页面调 `/recycle-bin`，主列表看不到这些

---

## 涉及的后端文件

| 文件 | 改动 |
|------|------|
| `app/agent/llm.py`（新） | LLM 客户端（关键词提取/分组/摘要） |
| `app/tools/feedback/integrator.py`（新） | 整合核心：原子化+两轮匹配+合并+回收站+降级 |
| `app/tools/feedback/models.py` | priority + 新字段 + `FeedbackRecycleBin` 表 |
| `app/tools/feedback/schemas.py` | P1-P4 + `IntegrateResult`/`RecycleBinResponse` |
| `app/tools/feedback/router.py` | severity→priority、BackgroundTasks 自动整合、`/integrate`、`/recycle-bin` |
| `app/tools/feedback/tool.py` | input_schema 更新 + `integrate` action |
| `app/common/db.py` | 迁移函数（检测旧 severity 列则重建） |
| `app/main.py` | lifespan 调迁移 |
| `app/config.py` / `.env` / `requirements.txt` | LLM 配置 + `openai` 依赖 |

---

## 前端实现与集成状态（已完成）

前端在 `tool-tester` 子项目中已完全适配上述后端变更，具体工作如下：

1. **全面字段适配**：
   - 将所有涉及 `severity` 的代码、状态、提交表单和展示字段全部重构为 `priority`（支持 `P1`、`P2`、`P3`、`P4` 四个优先级等级）。
   - 主列表与卡片渲染中移除 `severity` 图标/文字，替换为对应的 `priority` 标签及视觉样式。
2. **新增字段展示**：
   - 在反馈卡片详情中新增展示 `keywords`（关键词列表）、`evaluated`（是否已被评估）、`duplicate_count`（重复上报次数）、`group_summary`（LLM 生成的分组综合摘要）等核心智能化字段。
   - 当 `duplicate_count` > 1 时，卡片会以高亮标记展示“热点”重复数，并展示 LLM 的合并摘要。
3. **标签/关键词输入**：
   - 新增反馈的提交表单中集成了英文逗号/中文逗号分隔的 `keywords` 可选标签输入。
4. **新增「手动触发整合」端点对接**：
   - 顶部工具栏新增“手动触发整合”按钮，点击后向 `POST /api/tools/feedback/integrate` 发送请求，并以弹窗/通知形式展示返回的整合指标（如 `evaluated_count`、`merged_count`、`new_groups`、`priority_upgrades`、`method` 降级说明等）。
5. **新增「回收站」子标签页**：
   - 新增“回收站”独立选项卡，调用 `GET /api/tools/feedback/recycle-bin` 接口，以独立的列表形式向管理员展示已被合并归档的反馈单，并呈现其 `original_id`、`merged_into_id`、`merge_reason` 以及 `archived_at` 详情。
6. **构建与类型验证及防御性校验**：
   - 在数据请求（State 状态更新）与 TSX 视图渲染层（`.map()` 和 `.length` 调用前）均加入了双层防御性 `Array.isArray(...)` 校验。即使后端未来因为异常返回非数组结构，前端页面也会优雅降级，绝不发生白屏崩溃。
   - 清理了未使用的 React/TypeScript 导入与辅助函数，已在本地执行 `npm run build` 通过编译，无编译错误与类型不兼容问题。

如有后端接口逻辑进一步调整，可在本文件中补充，前端会及时跟进。

---

## 建议后端修复的问题 (Recommended Backend Fixes)

在联调中，前端发现以下后端路由定义冲突问题，导致 `/api/tools/feedback/recycle-bin` 请求会返回 422 校验失败：

### 1. 静态路由冲突（`/recycle-bin` 冲突）
- **现象**：当访问 `GET /api/tools/feedback/recycle-bin` 时，后端返回 HTTP 422 报错：`"input": "recycle-bin", "msg": "Input should be a valid integer..."`。
- **原因**：在 `app/tools/feedback/router.py` 中，动态路由 `@router.get('/{item_id}')` 定义在静态路由 `@router.get('/recycle-bin')` 之前。由于 FastAPI 的路由匹配是有序的，系统把 `"recycle-bin"` 误当成了整型的 `item_id` 进行解析，导致类型转换失败。
- **修复方案**：请在 `app/tools/feedback/router.py` 中，**将 `/recycle-bin` 的路由定义（包括其后的 `/integrate` 或其他静态路由）移到 `/{item_id}` 之前**。

例如，请调整路由声明顺序：
```python
# 1. 先声明静态路由
@router.get('/recycle-bin', response_model=list[RecycleBinResponse], summary='回收站列表')
def list_recycle_bin(...):
    ...

# 2. 后声明动态路由
@router.get('/{item_id}', response_model=FeedbackResponse, summary='反馈详情')
def get_feedback(item_id: int, ...):
    ...
```

