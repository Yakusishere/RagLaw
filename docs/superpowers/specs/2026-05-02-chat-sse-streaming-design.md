# 聊天接口 SSE 流式输出设计说明

**日期：** 2026-05-02

**范围：** `law_helper` 后端聊天能力增强

## 1. 目标

在不破坏现有问答接口契约的前提下，为聊天能力增加 SSE 流式输出能力，使前端可以边接收边渲染回答正文，同时在流结束时拿到完整引用与检索元信息。

本次改造的直接目标：

- 保留现有 `POST /chat` JSON 接口
- 新增 `POST /chat/stream` SSE 接口
- 复用当前 retrieval 与 grounded answer 流程
- 保持 DashScope/OpenAI-compatible provider 可用
- 为前端提供稳定、简单的事件协议

## 2. 非目标

本次不包含：

- 废弃或替换现有 `POST /chat`
- 多轮会话记忆
- 前端实现
- WebSocket
- 结构化 token 级 citation 对齐
- `/retrieve` 的流式化

## 3. 现状

当前后端已经具备：

- `POST /chat`
  - 输入 `query`
  - 内部执行 retrieval
  - 调用 LLM 返回完整 `ChatResponse`
- `POST /retrieve`
  - 返回完整引用化检索结果
- OpenAI-compatible provider 配置
  - `OPENAI_API_KEY`
  - `OPENAI_BASE_URL`
  - `OPENAI_MODEL`
  - `OPENAI_EMBEDDING_MODEL`

当前 `POST /chat` 的问题是：

- 只有完整响应，不能逐步显示回答
- 前端必须等待上游模型全部完成后才能看到正文

## 4. 总体方案

采用“保留旧接口 + 新增流式接口”的兼容方案。

### 4.1 接口策略

- 保留：`POST /chat`
  - 继续返回 `ChatResponse`
- 新增：`POST /chat/stream`
  - 返回 `text/event-stream`

原因：

- 不破坏现有前端契约
- 允许旧页面继续使用完整 JSON
- 新页面可以逐步切换到流式消费
- 测试和联调风险最低

### 4.2 请求体

`POST /chat/stream` 第一版保持与 `POST /chat` 一致：

```json
{
  "query": "商家拒绝退款怎么办"
}
```

第一版不新增：

- `top_k`
- 会话 ID
- 历史消息

## 5. SSE 事件协议

### 5.1 事件类型

流中只定义 5 类事件：

- `meta`
- `delta`
- `citations`
- `done`
- `error`

### 5.2 事件顺序

正常顺序：

1. `meta`
2. `delta`（0 次或多次）
3. `citations`
4. `done`

异常顺序：

1. `meta`（可选，若请求已通过基础处理）
2. `error`

### 5.3 事件载荷

#### `meta`

开头发送一次，用于告诉前端当前问题文本。

```json
{
  "query": "商家拒绝退款怎么办"
}
```

#### `delta`

持续发送回答正文片段。前端只需要把 `text` 追加到当前显示文本即可。

```json
{
  "text": "根据现有检索材料，"
}
```

#### `citations`

正文流完成后统一发送一次，不夹在 token 流中。

```json
{
  "citations": [],
  "retrieval": {
    "result_count": 8
  },
  "basis": [
    "《中华人民共和国消费者权益保护法》第二十四条"
  ],
  "insufficient_basis": false,
  "suggested_steps": [
    "保留证据并先向商家主张退换或赔偿。"
  ],
  "risk_notes": [
    "模型回答受限于当前检索材料。"
  ]
}
```

#### `done`

结束标记。

```json
{
  "ok": true
}
```

#### `error`

异常标记。

```json
{
  "message": "上游模型调用失败"
}
```

### 5.4 为什么不用“每个 token 都带 citation”

第一阶段目标是让前端尽快可用，而不是做复杂的流式对齐协议。

如果每个 token 都夹带引用或结构化状态：

- 前端状态机会明显复杂
- 后端事件拼装更脆弱
- 对当前 DashScope/OpenAI-compatible provider 兼容性没有明显收益

因此第一版采用：

- `delta` 只管正文
- `citations` 在结尾统一返回结构化信息

## 6. 服务层设计

### 6.1 Retrieval 复用

`POST /chat/stream` 必须和 `POST /chat` 一样，先复用现有 retrieval 流程。

步骤：

1. 接收 `query`
2. 执行 `RetrievalService.retrieve()`
3. 用检索结果构造 grounded prompt
4. 调用模型流式输出
5. 将输出转成 SSE 事件

### 6.2 LLMService 改造

保留：

- `answer(retrieval_response) -> ChatResponse`

新增：

- `stream_answer(retrieval_response) -> iterator`

`stream_answer()` 的职责：

- 接收 `RetrievalResponse`
- 若无检索结果，直接产出“依据不足”事件序列
- 若有检索结果，调用 provider 的流式接口
- 将 provider 的增量文本转换为 `delta`
- 在结束时补发 `citations`

### 6.3 依据不足场景

当 `retrieval_response.results` 为空时，不调用真实流式模型，直接按以下顺序返回：

1. `meta`
2. `delta`
3. `citations`
4. `done`

正文内容保持与当前 JSON 接口一致的降级语义，例如：

- “依据不足，当前检索结果未提供足够法条依据。”

### 6.4 结构化尾部信息

为避免前端只能拿到纯文本，`citations` 事件中统一返回：

- `citations`
- `retrieval.result_count`
- `basis`
- `insufficient_basis`
- `suggested_steps`
- `risk_notes`

这样前端在流式模式下仍然能拿到与 `POST /chat` 接近的结构化信息。

## 7. API 层设计

### 7.1 新路由

新增：

- `POST /chat/stream`

返回类型：

- `StreamingResponse`
- `media_type="text/event-stream"`

### 7.2 编码格式

每个事件按标准 SSE 形式返回：

```text
event: delta
data: {"text":"..."}

```

要求：

- JSON 使用 UTF-8
- 中文正文不能被编码成乱码
- 每个事件之间空一行

## 8. 错误处理

### 8.1 路由级错误

请求体校验失败：

- 保持 FastAPI 默认 `422`

### 8.2 流内错误

如果请求已进入流式阶段，但上游模型调用失败：

- 尽量发送 `error` 事件
- 然后结束连接

### 8.3 Provider 兼容性

当前系统使用 OpenAI-compatible SDK 接 DashScope。

本次实现应遵守：

- 不依赖 OpenAI 专属且 DashScope 不支持的流式字段
- 使用当前 provider 能稳定提供的最小流式文本能力
- 若 provider 流式接口行为与非流式接口有差异，应以兼容 DashScope 为第一优先级

## 9. 测试策略

### 9.1 单元测试

新增/补充：

- `LLMService.stream_answer()` 在有检索结果时：
  - 产出 `meta -> delta* -> citations -> done`
- `LLMService.stream_answer()` 在无检索结果时：
  - 产出“依据不足”路径
- 上游异常时：
  - 产出 `error`

测试重点：

- 事件顺序
- 关键字段
- 尾部结构化信息

不测试重点：

- 具体模型文案内容

### 9.2 API 集成测试

新增：

- `/chat/stream` 集成测试

至少验证：

- 返回类型为 `text/event-stream`
- 包含 `event:` 和 `data:` 行
- 正常路径能收到 `delta`
- 结束时能收到 `citations` 与 `done`

### 9.3 真实联调

真实联调至少覆盖：

- `商家拒绝退款怎么办`
- `网购商品质量有问题但商家不同意退货怎么办`
- `平台内商家虚假宣传如何维权`

联调重点：

- 是否持续收到增量正文
- 中文是否乱码
- 结尾是否稳定收到 `citations`
- DashScope 兼容模式下是否中途断流

## 10. 文档更新

需要更新：

- `docs/frontend_api_contract.md`

更新内容：

- 保留现有 `POST /chat` JSON 文档
- 新增 `POST /chat/stream` 契约
- 给出 SSE 事件说明
- 给出前端消费建议

## 11. 实施边界

本次只做最小可用 SSE 能力，不顺手扩展：

- 不加多轮会话
- 不加历史消息
- 不加 WebSocket
- 不改 `/retrieve`
- 不改变现有 `ChatResponse` JSON 结构

## 12. 结论

本次正确落点是：

- 保留 `POST /chat`
- 新增 `POST /chat/stream`
- 用统一 retrieval 结果驱动 JSON 与 SSE 两种输出
- 让前端用最简单的事件协议接流
- 在流末尾一次性补发引用与元信息

这是当前阶段风险最低、兼容性最好、实现成本最可控的方案。
