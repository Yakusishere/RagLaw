# Upstream Dependency Error Handling Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make embedding and LLM upstream failures return stable `502` responses on synchronous APIs while preserving SSE `error` events on `/chat/stream`.

**Architecture:** Normalize external dependency failures at the dependency/service entry points, then catch only that project-level exception in the API layer. Keep database errors and local bugs unwrapped so they still surface as `500`, and keep `/chat/stream` on its existing event-based failure contract.

**Tech Stack:** FastAPI, pytest, Pydantic, existing OpenAI SDK integration, SSE streaming.

---

## File Structure

- `app/services/exceptions.py`
  - Introduce or rename the project-level upstream dependency exception.
- `app/dependencies.py`
  - Normalize embedding client failures to the project-level exception.
- `app/services/llm_service.py`
  - Align LLM create/stream failure handling with the same exception type and stable message.
- `app/api/retrieve.py`
  - Convert the project-level exception to HTTP `502`.
- `app/api/chat.py`
  - Convert synchronous retrieval/LLM upstream failures to `502` and keep SSE `error` output for streaming.
- `app/api/draft.py`
  - Align draft API exception handling with the renamed/shared exception.
- `tests/unit/test_dependencies.py`
  - Add embedding-client normalization tests.
- `tests/unit/test_llm_service.py`
  - Update assertions to the unified exception type and message.
- `tests/integration/test_retrieve_api.py`
  - Add `/retrieve` `502` behavior tests.
- `tests/integration/test_chat_api.py`
  - Add `/chat` retrieval-upstream `502` test and align stream error assertions.
- `tests/integration/test_draft_api.py`
  - Align draft API tests with the unified exception type.

### Task 1: Normalize External Dependency Exceptions

**Files:**
- Modify: `app/services/exceptions.py`
- Modify: `app/dependencies.py`
- Modify: `app/services/llm_service.py`
- Modify: `tests/unit/test_dependencies.py`
- Modify: `tests/unit/test_llm_service.py`

- [ ] **Step 1: Write failing unit tests for embedding and LLM exception normalization**

```python
from app.dependencies import OpenAIEmbeddingClient
from app.services.exceptions import UpstreamDependencyError


def test_embedding_client_normalizes_upstream_failure():
    class ExplodingEmbeddings:
        def create(self, **kwargs):
            raise ValueError("boom")

    class FakeClient:
        embeddings = ExplodingEmbeddings()

    client = OpenAIEmbeddingClient(
        api_key="test-key",
        model_name="test-embedding",
        client=FakeClient(),
    )

    try:
        client.embed_query("商家拒绝退款怎么办")
        raise AssertionError("expected UpstreamDependencyError")
    except UpstreamDependencyError as exc:
        assert str(exc) == "上游依赖调用失败"
        assert isinstance(exc.__cause__, ValueError)
```

```python
from app.services.exceptions import UpstreamDependencyError


def test_answer_normalizes_upstream_create_failure():
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=FakeOpenAIClient(create_exc=ValueError("boom")),
    )

    try:
        service.answer(build_retrieval_response())
        raise AssertionError("expected UpstreamDependencyError")
    except UpstreamDependencyError as exc:
        assert str(exc) == "上游依赖调用失败"
        assert isinstance(exc.__cause__, ValueError)
```

- [ ] **Step 2: Run the targeted unit tests and verify they fail**

Run: `PYTHONPATH=. python -m pytest tests/unit/test_dependencies.py tests/unit/test_llm_service.py -q`  
Expected: FAIL because `OpenAIEmbeddingClient` does not yet accept an injected client, embedding failures are not normalized, and the tests still expect the old exception type/message.

- [ ] **Step 3: Implement the unified upstream dependency exception and normalize call sites**

```python
# app/services/exceptions.py
class UpstreamDependencyError(RuntimeError):
    def __init__(self, message: str = "上游依赖调用失败") -> None:
        super().__init__(message)


UpstreamModelError = UpstreamDependencyError
```

```python
# app/dependencies.py
class OpenAIEmbeddingClient:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        base_url: str | None = None,
        client: OpenAI | None = None,
    ):
        self._client = client or OpenAI(api_key=api_key, base_url=base_url)
        self._model_name = model_name

    def embed_query(self, query: str) -> list[float]:
        try:
            response = self._client.embeddings.create(model=self._model_name, input=query)
        except Exception as exc:
            raise UpstreamDependencyError() from exc
        return response.data[0].embedding
```

```python
# app/services/llm_service.py
from app.services.exceptions import UpstreamDependencyError

...
        except Exception as exc:
            raise UpstreamDependencyError() from exc
...
        except Exception:
            yield ChatStreamEvent(event="error", data={"message": str(UpstreamDependencyError())})
            return
...
        except Exception as exc:
            raise UpstreamDependencyError() from exc
```

- [ ] **Step 4: Re-run the targeted unit tests and verify they pass**

Run: `PYTHONPATH=. python -m pytest tests/unit/test_dependencies.py tests/unit/test_llm_service.py -q`  
Expected: PASS

- [ ] **Step 5: Commit the exception normalization changes**

```bash
git add app/services/exceptions.py app/dependencies.py app/services/llm_service.py tests/unit/test_dependencies.py tests/unit/test_llm_service.py
git commit -m "refactor: unify upstream dependency errors"
```

### Task 2: Apply Stable `502` Handling to Synchronous APIs

**Files:**
- Modify: `app/api/retrieve.py`
- Modify: `app/api/chat.py`
- Modify: `app/api/draft.py`
- Modify: `tests/integration/test_retrieve_api.py`
- Modify: `tests/integration/test_chat_api.py`
- Modify: `tests/integration/test_draft_api.py`

- [ ] **Step 1: Add failing integration tests for `/retrieve` and retrieval-stage `/chat` upstream failures**

```python
from app.services.exceptions import UpstreamDependencyError


class FakeFailingRetrievalService:
    def retrieve(self, query: str, top_k: int | None = None):
        raise UpstreamDependencyError()


def test_retrieve_returns_502_when_upstream_dependency_call_fails():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeFailingRetrievalService()
    client = TestClient(app)

    response = client.post("/retrieve", json={"query": "商家拒绝退款怎么办"})

    assert response.status_code == 502
    assert response.json() == {"detail": "上游依赖调用失败"}
```

```python
def test_chat_returns_502_when_retrieval_upstream_call_fails():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeFailingRetrievalService()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()
    client = TestClient(app)

    response = client.post("/chat", json={"query": "商家拒绝退款怎么办"})

    assert response.status_code == 502
    assert response.json() == {"detail": "上游依赖调用失败"}
```

```python
def test_chat_stream_emits_error_event_when_retrieval_upstream_call_fails():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeFailingRetrievalService()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    client = TestClient(app)
    response, frames = collect_stream_frames(client, "商家拒绝退款怎么办")

    assert response.status_code == 200
    assert [parse_frame(frame)[0] for frame in frames] == ["error"]
    assert parse_frame(frames[0])[1]["message"] == "上游依赖调用失败"
```

- [ ] **Step 2: Run the integration tests and verify they fail**

Run: `PYTHONPATH=. python -m pytest tests/integration/test_retrieve_api.py tests/integration/test_chat_api.py tests/integration/test_draft_api.py -q`  
Expected: FAIL because `/retrieve` does not yet return `502` and `/chat` does not yet normalize retrieval-stage upstream failures.

- [ ] **Step 3: Implement API-layer `502` handling for the unified exception**

```python
# app/api/retrieve.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.exceptions import UpstreamDependencyError

...
    try:
        return service.retrieve(payload.query, payload.top_k)
    except UpstreamDependencyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

```python
# app/api/chat.py
from app.services.exceptions import UpstreamDependencyError

...
    try:
        retrieval_response = retrieval_service.retrieve(payload.query)
        return chat_service.answer(retrieval_response)
    except UpstreamDependencyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

```python
def stream_chat_events(...):
    try:
        retrieval_response = retrieval_service.retrieve(payload.query)
        for event in chat_service.stream_answer(retrieval_response):
            yield encode_sse_event(event)
    except UpstreamDependencyError as exc:
        yield encode_error_sse_event(str(exc))
```

```python
# app/api/draft.py
from app.services.exceptions import UpstreamDependencyError

...
    except UpstreamDependencyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
```

- [ ] **Step 4: Re-run the integration tests and verify they pass**

Run: `PYTHONPATH=. python -m pytest tests/integration/test_retrieve_api.py tests/integration/test_chat_api.py tests/integration/test_draft_api.py -q`  
Expected: PASS

- [ ] **Step 5: Commit the API error-handling changes**

```bash
git add app/api/retrieve.py app/api/chat.py app/api/draft.py tests/integration/test_retrieve_api.py tests/integration/test_chat_api.py tests/integration/test_draft_api.py
git commit -m "feat: return stable upstream dependency errors"
```

### Task 3: Full Verification and Real API Regression Check

**Files:**
- No new files required unless a regression fix is needed.

- [ ] **Step 1: Run the full backend test suite**

Run: `PYTHONPATH=. python -m pytest tests/unit tests/integration -q`  
Expected: PASS with all tests green.

- [ ] **Step 2: Run a real `/retrieve` upstream-failure regression check**

Run: `PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

Then reproduce with real environment:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/retrieve -ContentType "application/json" -Body '{"query":"商家拒绝退款怎么办"}'
```

Expected:

- if upstream embedding call succeeds, return normal retrieval payload
- if upstream embedding call fails, return HTTP `502` with `{"detail":"上游依赖调用失败"}`
- must not expose raw `httpx` or SDK connection text in the API response body

- [ ] **Step 3: Run a real `/draft` regression check on the same upstream path**

Use the same real request shape that was previously producing `500` during full `/draft` generation.

Expected:

- if upstream dependency succeeds, return normal draft payload
- if upstream dependency fails, return HTTP `502` instead of `500`

- [ ] **Step 4: If verification reveals a failure, debug the root cause before closing**

Run after the fix:

```bash
PYTHONPATH=. python -m pytest tests/unit tests/integration -q
```

Expected: PASS after the root-cause fix, not a one-off patch.

- [ ] **Step 5: Commit any verification-driven fix**

```bash
git add app tests
git commit -m "fix: harden upstream dependency error handling"
```

## Self-Review

- Spec coverage:
  - unified exception type: Task 1
  - `/retrieve` `502`: Task 2
  - `/chat` retrieval + LLM `502`: Task 1 + Task 2
  - `/draft` retrieval + LLM `502`: Task 1 + Task 2
  - `/chat/stream` SSE `error`: Task 1 + Task 2
  - real verification: Task 3
- Placeholder scan:
  - no `TBD`, `TODO`, or ambiguous implementation steps remain
- Type consistency:
  - unified error type is `UpstreamDependencyError`
  - stable message is `上游依赖调用失败`

Plan complete and saved to `docs/superpowers/plans/2026-05-04-upstream-dependency-error-handling.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints
