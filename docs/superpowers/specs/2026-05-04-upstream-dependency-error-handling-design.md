# Upstream Dependency Error Handling Design

**日期：** 2026-05-04  
**范围：** 统一 `retrieve` / `chat` / `draft` 三类后端接口在调用 embedding 或 LLM 等外部依赖失败时的错误行为，确保同步接口返回稳定的 `502`，流式接口保持 SSE `error` 事件语义。

## 1. 背景

当前项目已经具备：

- `POST /retrieve`
- `POST /chat`
- `POST /chat/stream`
- `POST /draft`

但这些接口对“上游依赖失败”的处理并不一致。

现状大致如下：

- `LLMService.answer()` / `draft_document()` 内部会把 OpenAI SDK 异常转成 `UpstreamModelError`
- `POST /chat` 与 `POST /draft` 会把 `UpstreamModelError` 转成 HTTP `502`
- `POST /retrieve` 当前没有对应保护
- `OpenAIEmbeddingClient.embed_query()` 当前也没有统一异常转换
- `POST /chat/stream` 当前通过 SSE `error` 事件传递流中错误，但对“retrieval 阶段的上游失败”仍可能混入普通异常语义

真实联调中已经出现过这种情况：

- embedding 上游连接失败
- `/draft` 因 retrieval 链路中未统一转换异常而直接返回 `500`

这会导致前端联调体验不稳定，因为前端无法根据统一规则判断“这是后端内部 bug”还是“外部模型服务暂时不可用”。

## 2. 目标与非目标

### 2.1 目标

1. embedding / LLM 外部依赖失败时，同步接口统一返回 HTTP `502`
2. `POST /chat/stream` 保持 SSE `error` 事件，不改成中途切换 HTTP 状态码
3. 数据库异常、代码 bug、本地逻辑错误仍保留原有 `500`
4. 测试能明确区分“上游依赖失败”和“本地服务失败”

### 2.2 非目标

- 不引入全局异常中间件
- 不统一所有异常为同一种错误
- 不改变 `404`、`422` 等已有业务/校验错误语义
- 不改变 `/chat/stream` 的既有事件结构

## 3. 方案选择

### 方案 A：API 层统一收敛外部依赖异常（采用）

做法：

- 在外部依赖调用点把 SDK/网络异常统一包成项目内异常
- 由 API 层按接口类型决定如何输出：
  - 同步接口：HTTP `502`
  - 流式接口：SSE `error`

优点：

- 与现有结构最一致
- 错误边界清晰
- 不会误伤数据库/代码错误
- 修改范围小，测试容易补齐

缺点：

- API 层仍需要少量 `try/except`

### 方案 B：service 层吞掉所有异常并直接生成最终响应

优点是 API 层更薄；缺点是 service 层会混入 HTTP/SSE 输出语义，不利于边界清晰。

### 方案 C：全局 FastAPI 异常处理器

优点是集中；缺点是当前项目规模不大，而且容易把同步接口与 SSE 接口的差异抹平，导致流式行为不够精确。

## 4. 核心设计

### 4.1 统一的错误语义

本次要表达的错误类型是：

- 外部 embedding 服务失败
- 外部 LLM 服务失败

这类错误的共同特点是：

- 问题发生在项目外部依赖
- 请求本身可能是合法的
- 后端本地代码与数据库未必有问题
- 对调用方来说更接近“网关/上游不可用”

因此统一使用 HTTP `502 Bad Gateway` 是合理的。

### 4.2 异常类型

当前已有：

- `UpstreamModelError`

它的名字偏向 “model”，但当前真实范围已经包括：

- chat LLM
- draft LLM
- embedding 调用

本次推荐将其调整为更泛化的项目内异常语义，二选一：

1. 保留类名 `UpstreamModelError`，但明确它也涵盖 embedding
2. 重命名为 `UpstreamDependencyError`

推荐使用方案 2，因为语义更准确，也更适合未来扩展到 reranker、OCR 等外部依赖。

### 4.3 异常抛出位置

#### `OpenAIEmbeddingClient.embed_query()`

当前这里直接调用 SDK：

- 一旦网络、认证、限流或上游不可用，会直接冒底层异常

本次调整为：

- 捕获 SDK / 网络相关异常
- 转换成 `UpstreamDependencyError`

#### `LLMService.answer()`

当前已经在内部做异常转换。  
本次只需同步到新的统一异常名。

#### `LLMService.draft_document()`

当前已经在内部做异常转换。  
本次只需同步到新的统一异常名。

#### `LLMService.stream_answer()`

当前流式方法本身不抛统一异常，而是：

- 流已开始后，捕获异常并直接 yield SSE `error`

这个行为应保留，因为：

- 流一旦开始，HTTP 状态已基本确定
- 前端当前也已经按 SSE `error` 事件消费

## 5. API 行为

### 5.1 `POST /retrieve`

新增行为：

- 若 embedding 上游调用失败，返回 HTTP `502`
- 响应格式：

```json
{
  "detail": "上游依赖调用失败"
}
```

数据库异常、repository 逻辑异常等仍保持默认 `500`。

### 5.2 `POST /chat`

统一行为：

- retrieval 阶段若 embedding 上游失败，返回 HTTP `502`
- answer 阶段若 LLM 上游失败，返回 HTTP `502`

也就是说 `/chat` 的两个外部依赖阶段都要收敛到同一错误语义。

### 5.3 `POST /draft`

统一行为：

- retrieval 阶段若 embedding 上游失败，返回 HTTP `502`
- drafting 阶段若 LLM 上游失败，返回 HTTP `502`

字段缺失、模板不存在等业务路径不受影响。

### 5.4 `POST /chat/stream`

保留现有契约：

- 若 retrieval 阶段就发生上游依赖失败，返回 SSE `error` 事件
- 若 stream 中途发生上游依赖失败，仍返回 SSE `error` 事件

本次只要求这类错误信息的来源统一，确保不会混入未包装的底层连接报错文本。

## 6. 错误信息文案

错误信息不应暴露底层 SDK 栈或网络细节。  
本次统一使用简洁、稳定、可前端直接展示的中文文案：

- `上游依赖调用失败`

如果后续要细分，也应以项目级稳定文案为主，而不是直接透传 `httpx` / `openai` 的原始异常字符串。

## 7. 代码边界

### 7.1 `app/services/exceptions.py`

负责定义统一的项目内异常类型。

### 7.2 `app/dependencies.py`

`OpenAIEmbeddingClient.embed_query()` 是 embedding 外部依赖入口，应在这里完成底层异常到项目异常的转换。

### 7.3 `app/services/llm_service.py`

LLM 外部依赖入口，应继续在这里完成底层异常到项目异常的转换。

### 7.4 `app/api/retrieve.py`

补齐对统一异常的 `502` 转换。

### 7.5 `app/api/chat.py`

同步接口继续返回 `502`；流式接口继续输出 SSE `error`，但错误来源改为统一异常。

### 7.6 `app/api/draft.py`

同步异常类型改为统一后的项目异常类型。

## 8. 测试设计

### 8.1 集成测试

至少新增或更新以下覆盖：

- `/retrieve` 在 retrieval service 抛统一上游异常时返回 `502`
- `/chat` 在 retrieval service 抛统一上游异常时返回 `502`
- `/chat` 在 chat service 抛统一上游异常时返回 `502`
- `/draft` 在 draft service 抛统一上游异常时返回 `502`
- `/chat/stream` 在 retrieval 阶段抛统一上游异常时输出 SSE `error`

### 8.2 单元测试

至少补一条：

- `OpenAIEmbeddingClient.embed_query()` 在底层 client 抛异常时，转换成统一项目异常

如果现有依赖测试文件更适合承载这条测试，可以直接放在 `tests/unit/test_dependencies.py`。

## 9. 风险与约束

### 风险 1：异常边界过宽

如果在过高层级直接 `except Exception`，容易把数据库错误也误转成 `502`。

控制方式：

- embedding client 只包自己的外部调用
- LLM service 只包自己的外部调用
- API 层只捕统一项目异常，不捕所有异常

### 风险 2：SSE 行为与同步接口混淆

若试图给 `/chat/stream` 也强行返回 HTTP `502`，会破坏当前前端消费逻辑。

控制方式：

- 明确区分同步和流式接口的输出语义

### 风险 3：错误文案不稳定

如果直接透传底层异常文本，前端联调会很难写稳定提示。

控制方式：

- 项目异常使用固定中文 message

## 10. 结论

本次采用“外部依赖入口统一抛项目异常，API 层按接口类型输出”的最小方案：

- embedding / LLM 失败：
  - `/retrieve`、`/chat`、`/draft` 返回 `502`
  - `/chat/stream` 返回 SSE `error`
- 数据库和本地代码错误仍保留 `500`
- 前端可以稳定地区分“后端内部故障”和“上游依赖失败”
