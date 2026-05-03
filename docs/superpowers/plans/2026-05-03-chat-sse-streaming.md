# Chat SSE Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a new `POST /chat/stream` SSE endpoint that streams grounded answer text while preserving the existing `POST /chat` JSON API.

**Architecture:** Keep retrieval unchanged and add a second output path on top of the existing chat flow. `LLMService` will expose both full-response and streaming methods, yielding semantic stream events that the API layer encodes into SSE frames. The existing `POST /chat` contract stays unchanged, while `POST /chat/stream` returns `text/event-stream` with `meta`, `delta`, `citations`, `done`, and `error` events.

**Tech Stack:** Python 3.11, FastAPI, StreamingResponse, OpenAI Python SDK `responses.stream`, Pydantic v2, pytest, FastAPI TestClient

---

## Planned File Structure

**Modify:**

- `app/schemas/chat.py`
- `app/services/llm_service.py`
- `app/api/chat.py`
- `tests/unit/test_llm_service.py`
- `tests/integration/test_chat_api.py`
- `docs/frontend_api_contract.md`
- `docs/backend_mvp_runbook.md`

**No new runtime modules required.**

The SSE event envelope stays in `app/schemas/chat.py` because it belongs to chat transport semantics. The API route handles SSE wire formatting, while `LLMService` only emits semantic events.

---

### Task 1: Add semantic chat stream events and LLM streaming service

**Files:**

- Modify: `app/schemas/chat.py`
- Modify: `app/services/llm_service.py`
- Modify: `tests/unit/test_llm_service.py`

- [ ] **Step 1: Write the failing unit tests for semantic stream events**

Update `tests/unit/test_llm_service.py` to cover:

- prompt assembly still works
- `stream_answer()` yields `meta -> delta* -> citations -> done` on success
- `stream_answer()` yields the insufficient-basis sequence without calling the upstream model
- `stream_answer()` yields `error` when the upstream stream raises

Use this test file content:

```python
from app.schemas.chat import ChatStreamEvent
from app.schemas.retrieval import CitationPayload, RetrievalResponse, RetrievalResultItem
from app.services.llm_service import LLMService, build_grounded_prompt


def build_retrieval_response() -> RetrievalResponse:
    return RetrievalResponse(
        query="商家拒绝退款怎么办",
        results=[
            RetrievalResultItem(
                chunk_id="law:1",
                doc_type="law",
                title="中华人民共和国消费者权益保护法",
                article_no="第二十四条",
                chunk_text="第二十四条 经营者提供的商品或者服务不符合质量要求的...",
                citation=CitationPayload(
                    chunk_id="law:1",
                    citation_label="《中华人民共和国消费者权益保护法》第二十四条",
                    title="中华人民共和国消费者权益保护法",
                    doc_type="law",
                    article_no="第二十四条",
                    effective_date="2013-10-25",
                    source_name="用户提供资料",
                    source_url="",
                ),
                scores={"vector_score": 0.9, "keyword_score": 0.7, "hybrid_score": 0.84},
            )
        ],
    )


class FakeResponseTextDeltaEvent:
    def __init__(self, delta: str):
        self.type = "response.output_text.delta"
        self.delta = delta


class FakeStream:
    def __init__(self, events):
        self._events = events

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        return None

    def __iter__(self):
        yield from self._events


class FakeResponsesAPI:
    def __init__(self, events=None, exc: Exception | None = None):
        self._events = events or []
        self._exc = exc

    def stream(self, **kwargs):
        if self._exc is not None:
            raise self._exc
        return FakeStream(self._events)


class FakeOpenAIClient:
    def __init__(self, events=None, exc: Exception | None = None):
        self.responses = FakeResponsesAPI(events=events, exc=exc)


def test_build_grounded_prompt_includes_citation_labels():
    response = build_retrieval_response()

    prompt = build_grounded_prompt(response)

    assert "《中华人民共和国消费者权益保护法》第二十四条" in prompt


def test_stream_answer_yields_meta_delta_citations_done():
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=FakeOpenAIClient(
            events=[
                FakeResponseTextDeltaEvent("根据现有检索材料，"),
                FakeResponseTextDeltaEvent("可以先主张退款。"),
            ]
        ),
    )

    events = list(service.stream_answer(build_retrieval_response()))

    assert [event.event for event in events] == ["meta", "delta", "delta", "citations", "done"]
    assert events[0].data["query"] == "商家拒绝退款怎么办"
    assert events[1].data["text"] == "根据现有检索材料，"
    assert events[3].data["basis"] == ["《中华人民共和国消费者权益保护法》第二十四条"]
    assert events[4].data == {"ok": True}


def test_stream_answer_returns_insufficient_basis_without_upstream_call():
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=FakeOpenAIClient(exc=AssertionError("should not call upstream")),
    )
    retrieval_response = RetrievalResponse(query="证据不足怎么办", results=[])

    events = list(service.stream_answer(retrieval_response))

    assert [event.event for event in events] == ["meta", "delta", "citations", "done"]
    assert events[1].data["text"] == "依据不足，当前检索结果未提供足够法条依据。"
    assert events[2].data["insufficient_basis"] is True
    assert events[2].data["retrieval"]["result_count"] == 0


def test_stream_answer_yields_error_when_upstream_stream_fails():
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=FakeOpenAIClient(exc=RuntimeError("boom")),
    )

    events = list(service.stream_answer(build_retrieval_response()))

    assert [event.event for event in events] == ["meta", "error"]
    assert "boom" in events[1].data["message"]
```

- [ ] **Step 2: Run the unit tests to verify they fail**

Run:

```bash
python -m pytest tests/unit/test_llm_service.py -q
```

Expected:

- FAIL because `ChatStreamEvent` does not exist
- FAIL because `LLMService.__init__()` does not accept `client`
- FAIL because `LLMService.stream_answer()` does not exist

- [ ] **Step 3: Add typed chat stream events and implement streaming in `LLMService`**

Update `app/schemas/chat.py` to add the stream event envelope:

```python
from typing import Any, Literal

from pydantic import BaseModel

from app.schemas.retrieval import CitationPayload


class ChatRequest(BaseModel):
    query: str


class ChatAnswer(BaseModel):
    summary: str
    basis: list[str]
    suggested_steps: list[str]
    risk_notes: list[str]
    insufficient_basis: bool


class ChatResponse(BaseModel):
    query: str
    answer: ChatAnswer
    citations: list[CitationPayload]
    retrieval: dict[str, int]


class ChatStreamEvent(BaseModel):
    event: Literal["meta", "delta", "citations", "done", "error"]
    data: dict[str, Any]
```

Update `app/services/llm_service.py` to accept an injected client and emit semantic stream events:

```python
from collections.abc import Iterator
from pathlib import Path

from openai import OpenAI

from app.schemas.chat import ChatAnswer, ChatResponse, ChatStreamEvent
from app.schemas.retrieval import RetrievalResponse


def build_grounded_prompt(retrieval_response: RetrievalResponse) -> str:
    context_blocks = []
    for item in retrieval_response.results:
        context_blocks.append(f"[{item.citation.citation_label}]\n{item.chunk_text}")
    joined_context = "\n\n".join(context_blocks) if context_blocks else "无可用检索依据。"
    return f"用户问题：{retrieval_response.query}\n\n检索依据：\n{joined_context}"


def build_insufficient_basis_answer() -> ChatAnswer:
    return ChatAnswer(
        summary="依据不足，当前检索结果未提供足够法条依据。",
        basis=[],
        suggested_steps=["补充交易记录、聊天记录、商品页面截图后再次检索。"],
        risk_notes=["当前回答不应视为确定法律结论。"],
        insufficient_basis=True,
    )


def build_supported_answer_parts(retrieval_response: RetrievalResponse) -> ChatAnswer:
    return ChatAnswer(
        summary="",
        basis=[item.citation.citation_label for item in retrieval_response.results[:3]],
        suggested_steps=["保留证据并先向商家主张退换或赔偿。"],
        risk_notes=["模型回答受限于当前检索材料。"],
        insufficient_basis=False,
    )


def build_stream_citations_payload(
    retrieval_response: RetrievalResponse,
    answer: ChatAnswer,
) -> dict[str, object]:
    return {
        "citations": [item.citation.model_dump(mode="json") for item in retrieval_response.results],
        "retrieval": {"result_count": len(retrieval_response.results)},
        "basis": answer.basis,
        "insufficient_basis": answer.insufficient_basis,
        "suggested_steps": answer.suggested_steps,
        "risk_notes": answer.risk_notes,
    }


class LLMService:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        client: OpenAI | None = None,
    ):
        self._client = client or OpenAI(api_key=api_key, base_url=base_url)
        self._model_name = model_name
        self._system_prompt = Path("app/prompts/qa_system.txt").read_text(encoding="utf-8")

    def answer(self, retrieval_response: RetrievalResponse) -> ChatResponse:
        if not retrieval_response.results:
            return ChatResponse(
                query=retrieval_response.query,
                answer=build_insufficient_basis_answer(),
                citations=[],
                retrieval={"result_count": 0},
            )

        prompt = build_grounded_prompt(retrieval_response)
        response = self._client.responses.create(
            model=self._model_name,
            input=[
                {"role": "system", "content": self._system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        text = response.output_text
        answer = build_supported_answer_parts(retrieval_response)
        answer.summary = text

        return ChatResponse(
            query=retrieval_response.query,
            answer=answer,
            citations=[item.citation for item in retrieval_response.results],
            retrieval={"result_count": len(retrieval_response.results)},
        )

    def stream_answer(self, retrieval_response: RetrievalResponse) -> Iterator[ChatStreamEvent]:
        yield ChatStreamEvent(event="meta", data={"query": retrieval_response.query})

        if not retrieval_response.results:
            answer = build_insufficient_basis_answer()
            yield ChatStreamEvent(event="delta", data={"text": answer.summary})
            yield ChatStreamEvent(
                event="citations",
                data=build_stream_citations_payload(retrieval_response, answer),
            )
            yield ChatStreamEvent(event="done", data={"ok": True})
            return

        prompt = build_grounded_prompt(retrieval_response)
        answer = build_supported_answer_parts(retrieval_response)

        try:
            with self._client.responses.stream(
                model=self._model_name,
                input=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
            ) as stream:
                for event in stream:
                    if event.type == "response.output_text.delta" and event.delta:
                        yield ChatStreamEvent(event="delta", data={"text": event.delta})
        except Exception as exc:
            yield ChatStreamEvent(event="error", data={"message": str(exc) or "上游模型调用失败"})
            return

        yield ChatStreamEvent(
            event="citations",
            data=build_stream_citations_payload(retrieval_response, answer),
        )
        yield ChatStreamEvent(event="done", data={"ok": True})
```

- [ ] **Step 4: Run the unit tests to verify they pass**

Run:

```bash
python -m pytest tests/unit/test_llm_service.py -q
```

Expected:

- PASS with 4 passed tests

- [ ] **Step 5: Commit**

```bash
git add app/schemas/chat.py app/services/llm_service.py tests/unit/test_llm_service.py
git commit -m "feat: add semantic chat streaming events"
```

---

### Task 2: Expose `/chat/stream` as SSE and add API integration tests

**Files:**

- Modify: `app/api/chat.py`
- Modify: `app/main.py`
- Modify: `tests/integration/test_chat_api.py`

- [ ] **Step 1: Write the failing integration tests for `/chat/stream`**

Update `tests/integration/test_chat_api.py` to keep the existing JSON test and add a streaming test:

```python
from fastapi.testclient import TestClient

from app.dependencies import get_chat_service, get_retrieval_service
from app.main import create_app
from app.schemas.chat import ChatAnswer, ChatResponse, ChatStreamEvent
from app.schemas.retrieval import CitationPayload, RetrievalResponse, RetrievalResultItem


class FakeRetrievalService:
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResponse:
        return RetrievalResponse(
            query=query,
            results=[
                RetrievalResultItem(
                    chunk_id="law:1",
                    doc_type="law",
                    title="中华人民共和国消费者权益保护法",
                    article_no="第二十四条",
                    chunk_text="第二十四条 经营者提供的商品或者服务不符合质量要求的...",
                    citation=CitationPayload(
                        chunk_id="law:1",
                        citation_label="《中华人民共和国消费者权益保护法》第二十四条",
                        title="中华人民共和国消费者权益保护法",
                        doc_type="law",
                        article_no="第二十四条",
                        effective_date="2013-10-25",
                        source_name="用户提供资料",
                        source_url="",
                    ),
                    scores={"vector_score": 0.9, "keyword_score": 0.7, "hybrid_score": 0.84},
                )
            ],
        )


class FakeChatService:
    def answer(self, retrieval_response: RetrievalResponse) -> ChatResponse:
        return ChatResponse(
            query=retrieval_response.query,
            answer=ChatAnswer(
                summary="可以先依据现有法条向商家主张退款。",
                basis=["《中华人民共和国消费者权益保护法》第二十四条"],
                suggested_steps=["先与商家协商并保留证据。"],
                risk_notes=["若证据不足，主张效果会受影响。"],
                insufficient_basis=False,
            ),
            citations=[retrieval_response.results[0].citation],
            retrieval={"result_count": 1},
        )

    def stream_answer(self, retrieval_response: RetrievalResponse):
        yield ChatStreamEvent(event="meta", data={"query": retrieval_response.query})
        yield ChatStreamEvent(event="delta", data={"text": "可以先依据现有法条"})
        yield ChatStreamEvent(
            event="citations",
            data={
                "citations": [retrieval_response.results[0].citation.model_dump(mode="json")],
                "retrieval": {"result_count": 1},
                "basis": ["《中华人民共和国消费者权益保护法》第二十四条"],
                "insufficient_basis": False,
                "suggested_steps": ["先与商家协商并保留证据。"],
                "risk_notes": ["若证据不足，主张效果会受影响。"],
            },
        )
        yield ChatStreamEvent(event="done", data={"ok": True})


def test_chat_returns_grounded_shape():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeRetrievalService()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    client = TestClient(app)
    response = client.post("/chat", json={"query": "商家拒绝退款怎么办"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"]["summary"]
    assert payload["citations"][0]["citation_label"] == "《中华人民共和国消费者权益保护法》第二十四条"
    assert payload["retrieval"]["result_count"] == 1


def test_chat_stream_returns_sse_frames():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeRetrievalService()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    client = TestClient(app)
    response = client.post("/chat/stream", json={"query": "商家拒绝退款怎么办"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: meta" in response.text
    assert 'data: {"query":"商家拒绝退款怎么办"}' in response.text
    assert "event: delta" in response.text
    assert "event: citations" in response.text
    assert "event: done" in response.text
```

- [ ] **Step 2: Run the integration tests to verify they fail**

Run:

```bash
python -m pytest tests/integration/test_chat_api.py -q
```

Expected:

- FAIL because `/chat/stream` does not exist

- [ ] **Step 3: Add SSE formatting and expose `/chat/stream`**

Update `app/api/chat.py` to add a formatter and streaming endpoint:

```python
import json
from collections.abc import Iterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_service, get_retrieval_service
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

router = APIRouter()


def encode_sse_event(event: ChatStreamEvent) -> str:
    payload = json.dumps(event.data, ensure_ascii=False, separators=(",", ":"))
    return f"event: {event.event}\ndata: {payload}\n\n"


def stream_chat_events(
    payload: ChatRequest,
    retrieval_service: RetrievalService,
    chat_service: LLMService,
) -> Iterator[str]:
    retrieval_response = retrieval_service.retrieve(payload.query)
    for event in chat_service.stream_answer(retrieval_response):
        yield encode_sse_event(event)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    chat_service: LLMService = Depends(get_chat_service),
) -> ChatResponse:
    retrieval_response = retrieval_service.retrieve(payload.query)
    return chat_service.answer(retrieval_response)


@router.post("/chat/stream")
def chat_stream(
    payload: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    chat_service: LLMService = Depends(get_chat_service),
) -> StreamingResponse:
    return StreamingResponse(
        stream_chat_events(payload, retrieval_service, chat_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

`app/main.py` should continue to include the same `chat_router`; no extra route registration is needed beyond the modified router module:

```python
from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.retrieve import router as retrieve_router


def create_app() -> FastAPI:
    app = FastAPI(title="law_helper backend", version="0.1.0")
    app.include_router(health_router)
    app.include_router(retrieve_router)
    app.include_router(chat_router)
    return app


app = create_app()
```

- [ ] **Step 4: Run the integration tests to verify they pass**

Run:

```bash
python -m pytest tests/integration/test_chat_api.py -q
```

Expected:

- PASS with 2 passed tests

- [ ] **Step 5: Commit**

```bash
git add app/api/chat.py tests/integration/test_chat_api.py
git commit -m "feat: add chat sse endpoint"
```

---

### Task 3: Document the SSE contract and local smoke-test flow

**Files:**

- Modify: `docs/frontend_api_contract.md`
- Modify: `docs/backend_mvp_runbook.md`

- [ ] **Step 1: Write the failing documentation delta as explicit target content**

Add a new `POST /chat/stream` section to `docs/frontend_api_contract.md` with:

- request body identical to `/chat`
- `text/event-stream` response type
- `meta`, `delta`, `citations`, `done`, `error` event descriptions
- a frontend note that `delta` should be appended as plain text and `citations` should be processed once at the end

Add a new smoke-test section to `docs/backend_mvp_runbook.md` with a `curl -N` example for SSE:

```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"商家拒绝退款怎么办\"}"
```

This step is intentionally “failing” in the sense that the docs do not yet describe the streaming interface, so the implementation remains undocumented.

- [ ] **Step 2: Update the docs**

Patch `docs/frontend_api_contract.md` by appending a stream section after the `POST /chat` section:

```md
### `POST /chat/stream`

用途：
- 基于检索结果生成流式问答结果
- 适合需要逐步渲染正文的前端页面

请求体：

```json
{
  "query": "商家拒绝退款怎么办"
}
```

响应类型：

- `text/event-stream`

事件说明：

- `meta`
  - 开头发送一次
  - `data` 示例：`{"query":"商家拒绝退款怎么办"}`
- `delta`
  - 增量正文片段
  - 前端应把 `data.text` 追加到当前回答文本
- `citations`
  - 流结束前统一发送一次
  - 包含 `citations`、`retrieval`、`basis`、`insufficient_basis`、`suggested_steps`、`risk_notes`
- `done`
  - 正常结束标记
- `error`
  - 异常结束标记

前端消费建议：

- 用 `delta` 渐进渲染正文
- 收到 `citations` 后再渲染引用区和附加说明
- 收到 `done` 后关闭当前加载状态
- 收到 `error` 后提示用户重试
```

Patch `docs/backend_mvp_runbook.md` to add the SSE smoke test command:

```md
```powershell
curl -N -X POST http://127.0.0.1:8000/chat/stream `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"商家拒绝退款怎么办\"}"
```
```

- [ ] **Step 3: Run the full automated suite**

Run:

```bash
python -m pytest tests/unit tests/integration -q
```

Expected:

- PASS with all unit and integration tests green

- [ ] **Step 4: Commit**

```bash
git add docs/frontend_api_contract.md docs/backend_mvp_runbook.md
git commit -m "docs: document chat sse contract"
```

---

### Task 4: Verify real provider streaming against DashScope compatibility mode

**Files:**

- Modify: `app/services/llm_service.py` only if real streaming exposes provider-specific incompatibilities
- Test: real local environment using `.env.local`

- [ ] **Step 1: Start the API locally**

Run:

```bash
uvicorn app.main:app --reload
```

Expected:

- local server starts cleanly on `http://127.0.0.1:8000`

- [ ] **Step 2: Run a real SSE smoke test against the local app**

Run:

```powershell
@'
import json
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import create_app

get_settings.cache_clear()
client = TestClient(create_app())
response = client.post("/chat/stream", json={"query": "商家拒绝退款怎么办"})
print(response.status_code)
print(response.headers.get("content-type"))
print(response.text[:1200])
'@ | python -
```

Expected:

- `200`
- content type starts with `text/event-stream`
- body contains `event: meta`, at least one `event: delta`, then `event: citations`, then `event: done`

- [ ] **Step 3: Run multi-case real streaming verification with network-enabled execution**

Run:

```powershell
@'
import json
from fastapi.testclient import TestClient
from app.config import get_settings
from app.main import create_app

queries = [
    "商家拒绝退款怎么办",
    "网购商品质量有问题但商家不同意退货怎么办",
    "平台内商家虚假宣传如何维权",
]

get_settings.cache_clear()
client = TestClient(create_app())

for query in queries:
    response = client.post("/chat/stream", json={"query": query})
    print("QUERY:", query)
    print("STATUS:", response.status_code)
    print(response.text[:1500])
    print("=" * 60)
'@ | python -
```

Expected:

- all cases return `200`
- SSE output contains readable Chinese deltas
- all cases end with `citations` and `done`
- no provider-specific stream crash

- [ ] **Step 4: If real verification exposes a provider-compatibility bug, fix the root cause before final completion**

Typical acceptable root-cause fixes include:

- switching from `responses.stream(...)` to `responses.create(..., stream=True)` if DashScope only supports that path reliably
- filtering event types more narrowly if the provider emits unexpected non-text stream events
- adjusting UTF-8 serialization only if the issue is encoding-related

Any fix in this step must:

- be verified with a new failing test first where feasible
- be re-run against the real provider afterward

- [ ] **Step 5: Commit final streaming compatibility fix if needed**

```bash
git add app/services/llm_service.py tests/unit/test_llm_service.py tests/integration/test_chat_api.py
git commit -m "fix: harden chat streaming provider compatibility"
```

---

## Self-Review

### Spec coverage

- Preserve existing `POST /chat`: covered in Tasks 1 and 2
- Add `POST /chat/stream`: covered in Task 2
- Use `meta`, `delta`, `citations`, `done`, `error`: covered in Tasks 1 and 2
- Retrieval reuse: covered in Tasks 1 and 2
- Insufficient-basis path: covered in Task 1
- Provider compatibility with DashScope/OpenAI-compatible setup: covered in Task 4
- Update frontend contract docs: covered in Task 3
- Real streaming verification: covered in Task 4

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain
- All code-writing tasks contain explicit code blocks
- All verification steps contain exact commands and expected outcomes

### Type consistency

- `ChatStreamEvent` is defined in `app/schemas/chat.py` and used consistently in tests, service, and API
- `LLMService.stream_answer()` yields `Iterator[ChatStreamEvent]`
- `encode_sse_event()` consumes `ChatStreamEvent`
- `POST /chat` continues returning `ChatResponse`

---

Plan complete and saved to `docs/superpowers/plans/2026-05-03-chat-sse-streaming.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
