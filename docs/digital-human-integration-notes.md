# Digital Human Integration Notes

这个仓库已经被 `digital-human-architecture` 里的数字人原型接入为真实工具后端。

维护本仓库时，请把下面这些点当成对外契约看待。工具库内部实现可以继续演进，但如果改动到这些接口或返回形状，数字人侧适配层就需要一起更新。

## 当前对接范围

数字人当前只依赖 3 类能力：

1. `GET /api/tools/rag/search`
2. `POST /api/tools/feedback`
3. `POST /api/tools/emergency/events`

数字人侧不会直接依赖本仓库内部 ORM、service、router 结构，但会依赖这些 HTTP 接口的路径、基础字段语义和响应可解析性。

## 尽量保持稳定的部分

### 1. 路由路径

请尽量不要随意修改下面这些路径：

- `/api/tools/rag/search`
- `/api/tools/feedback`
- `/api/tools/emergency/events`

如果确实要改，必须同步更新数字人仓库中的适配层：

- `C:\Users\27719\Desktop\repo\digital-human-architecture\prototypes\qwen-omni-audio-text\scenic_guide_client.py`
- `C:\Users\27719\Desktop\repo\digital-human-architecture\prototypes\qwen-omni-audio-text\tool_backend.py`

### 2. 基础请求字段

#### RAG search

当前数字人会传：

- `query`
- `top_k`

#### Feedback

当前数字人会传：

- `type`
- `priority`
- `scenic_spot`
- `description`
- `keywords`
- `contact_info`

#### Emergency

当前数字人会传：

- `type`
- `severity`
- `location`
- `description`
- `affected_areas`
- `reporter_info`

可以新增字段，但不要轻易删除这些字段或改变语义。

### 3. 基础响应字段

数字人当前主要会读取这些字段：

#### RAG search 响应

- `query`
- `top_k`
- `results`

`results` 中当前至少应可提供：

- `id`
- `title`
- `content`
- `category`
- `score`
- `source_type`

`retrieval_score` 可以为空；数字人侧允许没有它。

#### Feedback 响应

- `id`
- `type`
- `priority`
- `status`
- `keywords`

注意：
`keywords` 目前数字人侧既兼容 JSON 字符串，也兼容字符串数组，但更推荐逐步稳定为真正的数组。

#### Emergency 响应

- `id`
- `type`
- `severity`
- `location`
- `status`

## 可以自由调整的部分

下面这些一般不会直接影响数字人，只要上面的契约没破：

- 内部表结构
- ORM 模型命名
- service / router 拆分方式
- 检索策略
- 预热策略
- 日志结构
- 管理端、压测、前端测试页

## 当前已知事实

1. 数字人侧已经做了中间层解耦，不会直接依赖本仓库内部代码，只通过 HTTP 和适配层对接。
2. 当前知识库以景点、门票、路线、开放时间为主，缺少厕所、卖水、游客中心等设施类真实数据。
3. 当前数字人链路要求尽量基于真实数据作答，不建议为了补齐问答而写入虚构设施信息。

## 推荐维护方式

如果你要更新工具库，建议按这个顺序做：

1. 先确认是否会影响上述 3 个对接接口
2. 如果会影响，先在本文件补充说明
3. 再同步更新数字人仓库中的适配层
4. 最后做一轮数字人侧联调测试

## 联调提醒

数字人仓库中的关键对接文件：

- `C:\Users\27719\Desktop\repo\digital-human-architecture\prototypes\qwen-omni-audio-text\scenic_guide_client.py`
- `C:\Users\27719\Desktop\repo\digital-human-architecture\prototypes\qwen-omni-audio-text\tool_backend.py`
- `C:\Users\27719\Desktop\repo\digital-human-architecture\prototypes\qwen-omni-audio-text\tool_registry.py`

如果这边改了接口但那边没同步，最常见的结果是：

- 工具调用超时
- 字段解析失败
- 数字人拿到空结果
- 数字人误以为“查不到”
