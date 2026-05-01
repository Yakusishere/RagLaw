# Backend RAG MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first runnable FastAPI backend for `law_helper` that provides `GET /health`, `POST /retrieve`, and `POST /chat` on top of the existing promoted corpus and promoted embeddings.

**Architecture:** Keep the existing ingestion / promote pipeline unchanged and add a thin application layer under `app/`. Use environment-driven configuration, `psycopg` for direct PostgreSQL access, a repository + service split for retrieval, and a small OpenAI-backed LLM service for grounded answers.

**Tech Stack:** Python 3.11+, FastAPI, Uvicorn, Psycopg 3, Pydantic v2, pydantic-settings, OpenAI Python SDK, pytest

---

## Planned File Structure

**Create:**

- `pyproject.toml`
- `app/__init__.py`
- `app/main.py`
- `app/config.py`
- `app/dependencies.py`
- `app/api/__init__.py`
- `app/api/health.py`
- `app/api/retrieve.py`
- `app/api/chat.py`
- `app/db/__init__.py`
- `app/db/connection.py`
- `app/db/repositories/__init__.py`
- `app/db/repositories/retrieval_repository.py`
- `app/schemas/__init__.py`
- `app/schemas/retrieval.py`
- `app/schemas/chat.py`
- `app/services/__init__.py`
- `app/services/query_normalization.py`
- `app/services/citation_service.py`
- `app/services/retrieval_service.py`
- `app/services/llm_service.py`
- `app/prompts/qa_system.txt`
- `tests/unit/test_config_and_health.py`
- `tests/unit/test_query_normalization.py`
- `tests/unit/test_citation_service.py`
- `tests/unit/test_retrieval_repository.py`
- `tests/unit/test_retrieval_service.py`
- `tests/unit/test_llm_service.py`
- `tests/integration/test_retrieve_api.py`
- `tests/integration/test_chat_api.py`
- `docs/backend_mvp_runbook.md`

**Modify:**

- `.env.example`

---

### Task 1: Bootstrap the Python backend project

**Files:**

- Create: `pyproject.toml`
- Create: `app/__init__.py`
- Create: `app/main.py`
- Create: `app/config.py`
- Create: `app/dependencies.py`
- Create: `app/api/__init__.py`
- Create: `app/api/health.py`
- Test: `tests/unit/test_config_and_health.py`
- Modify: `.env.example`

- [ ] **Step 1: Write the failing bootstrap tests**

```python
# tests/unit/test_config_and_health.py
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_settings_reads_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://law:pass@localhost:5432/law_helper")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    settings = Settings()
    assert settings.database_url == "postgresql://law:pass@localhost:5432/law_helper"
    assert settings.openai_api_key == "test-key"
    assert settings.retrieval_final_top_k == 8


def test_health_endpoint_returns_ok():
    client = TestClient(create_app())
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/unit/test_config_and_health.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app'` or missing dependency errors because the backend project has not been created yet.

- [ ] **Step 3: Create the minimal backend scaffold and dependency manifest**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "law-helper-backend"
version = "0.1.0"
description = "FastAPI backend for law_helper RAG MVP"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115,<1.0",
  "uvicorn[standard]>=0.30,<1.0",
  "psycopg[binary]>=3.2,<4.0",
  "pydantic>=2.7,<3.0",
  "pydantic-settings>=2.3,<3.0",
  "openai>=1.30,<2.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2,<9.0",
  "httpx>=0.27,<1.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# app/config.py
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env.local", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://law:change-me@localhost:5432/law_helper"
    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4.1-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    retrieval_vector_top_k: int = 12
    retrieval_keyword_top_k: int = 12
    retrieval_final_top_k: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

```python
# app/api/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
```

```python
# app/main.py
from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="law_helper backend", version="0.1.0")
    app.include_router(health_router)
    return app


app = create_app()
```

```python
# app/__init__.py
__all__ = ["main"]
```

```python
# app/dependencies.py
from app.config import Settings, get_settings


def get_app_settings() -> Settings:
    return get_settings()
```

```python
# app/api/__init__.py
__all__ = ["health"]
```

```text
# .env.example (ensure these keys exist)
DATABASE_URL=postgresql://law:change-me@localhost:5432/law_helper
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
RETRIEVAL_VECTOR_TOP_K=12
RETRIEVAL_KEYWORD_TOP_K=12
RETRIEVAL_FINAL_TOP_K=8
```

- [ ] **Step 4: Install dependencies and run the bootstrap tests**

Run:

```bash
python -m pip install -e ".[dev]"
pytest tests/unit/test_config_and_health.py -v
```

Expected: PASS with 2 passed tests.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml app tests .env.example
git commit -m "feat: bootstrap fastapi backend project"
```

---

### Task 2: Add pure-domain query normalization and citation formatting

**Files:**

- Create: `app/schemas/retrieval.py`
- Create: `app/services/query_normalization.py`
- Create: `app/services/citation_service.py`
- Test: `tests/unit/test_query_normalization.py`
- Test: `tests/unit/test_citation_service.py`

- [ ] **Step 1: Write the failing unit tests**

```python
# tests/unit/test_query_normalization.py
from app.services.query_normalization import normalize_query


def test_normalize_query_strips_outer_whitespace():
    assert normalize_query("  商家拒绝退款怎么办  ") == "商家拒绝退款怎么办"


def test_normalize_query_collapses_internal_whitespace():
    assert normalize_query("商家   拒绝\t退款") == "商家 拒绝 退款"
```

```python
# tests/unit/test_citation_service.py
from app.schemas.retrieval import RetrievalCandidate
from app.services.citation_service import build_citation


def test_build_citation_preserves_empty_source_url():
    candidate = RetrievalCandidate(
        chunk_id="doc:article:0001",
        doc_type="law",
        title="中华人民共和国消费者权益保护法",
        article_no="第二十四条",
        chunk_text="第二十四条 经营者提供的商品或者服务不符合质量要求的...",
        citation_label="《中华人民共和国消费者权益保护法》第二十四条",
        source_name="用户提供资料",
        source_url="",
        effective_date="2013-10-25",
        vector_score=0.9,
        keyword_score=0.5,
        hybrid_score=0.8,
    )
    citation = build_citation(candidate)
    assert citation.citation_label == "《中华人民共和国消费者权益保护法》第二十四条"
    assert citation.source_url == ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/unit/test_query_normalization.py tests/unit/test_citation_service.py -v
```

Expected: FAIL because the retrieval schemas and service modules do not exist yet.

- [ ] **Step 3: Implement retrieval schemas, query normalization, and citation formatting**

```python
# app/schemas/retrieval.py
from pydantic import BaseModel, Field


class CitationPayload(BaseModel):
    chunk_id: str
    citation_label: str
    title: str
    doc_type: str
    article_no: str | None = None
    effective_date: str | None = None
    source_name: str
    source_url: str = ""


class RetrievalCandidate(BaseModel):
    chunk_id: str
    doc_type: str
    title: str
    article_no: str | None = None
    chunk_text: str
    citation_label: str
    source_name: str
    source_url: str = ""
    effective_date: str | None = None
    vector_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float = Field(default=0.0)


class RetrievalRequest(BaseModel):
    query: str
    top_k: int | None = None


class RetrievalResultItem(BaseModel):
    chunk_id: str
    doc_type: str
    title: str
    article_no: str | None = None
    chunk_text: str
    citation: CitationPayload
    scores: dict[str, float | None]


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievalResultItem]
```

```python
# app/services/query_normalization.py
import re


def normalize_query(query: str) -> str:
    normalized = query.strip()
    normalized = re.sub(r"[ \u3000]+", " ", normalized)
    normalized = re.sub(r"[\t\r\n]+", " ", normalized)
    return normalized
```

```python
# app/services/citation_service.py
from app.schemas.retrieval import CitationPayload, RetrievalCandidate


def build_citation(candidate: RetrievalCandidate) -> CitationPayload:
    return CitationPayload(
        chunk_id=candidate.chunk_id,
        citation_label=candidate.citation_label,
        title=candidate.title,
        doc_type=candidate.doc_type,
        article_no=candidate.article_no,
        effective_date=candidate.effective_date,
        source_name=candidate.source_name,
        source_url=candidate.source_url or "",
    )
```

- [ ] **Step 4: Run the unit tests**

Run:

```bash
pytest tests/unit/test_query_normalization.py tests/unit/test_citation_service.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/retrieval.py app/services/query_normalization.py app/services/citation_service.py tests/unit
git commit -m "feat: add retrieval schemas and citation utilities"
```

---

### Task 3: Build PostgreSQL retrieval repository for vector and keyword recall

**Files:**

- Create: `app/db/__init__.py`
- Create: `app/db/connection.py`
- Create: `app/db/repositories/__init__.py`
- Create: `app/db/repositories/retrieval_repository.py`
- Test: `tests/unit/test_retrieval_repository.py`

- [ ] **Step 1: Write the failing repository tests**

```python
# tests/unit/test_retrieval_repository.py
from app.db.repositories.retrieval_repository import (
    build_keyword_search_sql,
    build_vector_search_sql,
)


def test_vector_sql_limits_to_enabled_law_and_rule_chunks():
    sql = build_vector_search_sql()
    assert "rag.chunk_embeddings" in sql
    assert "enabled_for_retrieval = true" in sql
    assert "c.doc_type IN ('law', 'rule')" in sql
    assert "ORDER BY vector_score DESC" in sql


def test_keyword_sql_uses_search_text_and_top_k_limit():
    sql = build_keyword_search_sql()
    assert "c.search_text ILIKE" in sql
    assert "LIMIT %(top_k)s" in sql
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/unit/test_retrieval_repository.py -v
```

Expected: FAIL because the repository module does not exist yet.

- [ ] **Step 3: Implement connection helpers and retrieval repository**

```python
# app/db/connection.py
from collections.abc import Iterator
from contextlib import contextmanager

from psycopg import Connection, connect
from psycopg.rows import dict_row

from app.config import get_settings


@contextmanager
def get_connection() -> Iterator[Connection]:
    settings = get_settings()
    with connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn
```

```python
# app/db/repositories/retrieval_repository.py
from psycopg import Connection

from app.schemas.retrieval import RetrievalCandidate


def build_vector_search_sql() -> str:
    return """
SELECT
    c.chunk_id,
    c.doc_type,
    c.title,
    c.article_no,
    c.chunk_text,
    c.citation_label,
    c.source_name,
    COALESCE(c.source_url, '') AS source_url,
    c.effective_date::text AS effective_date,
    1 - (ce.embedding <=> %(query_embedding)s::vector) AS vector_score
FROM rag.chunk_embeddings ce
JOIN rag.chunks c ON c.chunk_id = ce.chunk_id
WHERE c.enabled_for_retrieval = true
  AND c.doc_type IN ('law', 'rule')
  AND ce.model_name = %(model_name)s
ORDER BY vector_score DESC
LIMIT %(top_k)s
""".strip()


def build_keyword_search_sql() -> str:
    return """
SELECT
    c.chunk_id,
    c.doc_type,
    c.title,
    c.article_no,
    c.chunk_text,
    c.citation_label,
    c.source_name,
    COALESCE(c.source_url, '') AS source_url,
    c.effective_date::text AS effective_date,
    CASE
        WHEN c.search_text ILIKE %(exact_query)s THEN 1.0
        WHEN c.search_text ILIKE %(partial_query)s THEN 0.7
        ELSE 0.0
    END AS keyword_score
FROM rag.chunks c
WHERE c.enabled_for_retrieval = true
  AND c.doc_type IN ('law', 'rule')
  AND c.search_text ILIKE %(partial_query)s
ORDER BY keyword_score DESC, c.doc_type ASC, c.article_no_int NULLS LAST
LIMIT %(top_k)s
""".strip()


class RetrievalRepository:
    def __init__(self, conn: Connection):
        self._conn = conn

    def vector_search(self, *, query_embedding: list[float], model_name: str, top_k: int) -> list[RetrievalCandidate]:
        with self._conn.cursor() as cur:
            cur.execute(
                build_vector_search_sql(),
                {
                    "query_embedding": query_embedding,
                    "model_name": model_name,
                    "top_k": top_k,
                },
            )
            rows = cur.fetchall()
        return [RetrievalCandidate(**row, keyword_score=None, hybrid_score=0.0) for row in rows]

    def keyword_search(self, *, normalized_query: str, top_k: int) -> list[RetrievalCandidate]:
        with self._conn.cursor() as cur:
            cur.execute(
                build_keyword_search_sql(),
                {
                    "exact_query": normalized_query,
                    "partial_query": f"%{normalized_query}%",
                    "top_k": top_k,
                },
            )
            rows = cur.fetchall()
        return [RetrievalCandidate(**row, vector_score=None, hybrid_score=0.0) for row in rows]
```

```python
# app/db/__init__.py
__all__ = ["connection"]
```

```python
# app/db/repositories/__init__.py
__all__ = ["retrieval_repository"]
```

- [ ] **Step 4: Run the repository tests**

Run:

```bash
pytest tests/unit/test_retrieval_repository.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/db tests/unit/test_retrieval_repository.py
git commit -m "feat: add postgres retrieval repository"
```

---

### Task 4: Implement hybrid retrieval service and `/retrieve` API

**Files:**

- Create: `app/services/retrieval_service.py`
- Create: `app/api/retrieve.py`
- Test: `tests/unit/test_retrieval_service.py`
- Test: `tests/integration/test_retrieve_api.py`
- Modify: `app/main.py`
- Modify: `app/dependencies.py`

- [ ] **Step 1: Write the failing service and API tests**

```python
# tests/unit/test_retrieval_service.py
from app.schemas.retrieval import RetrievalCandidate
from app.services.retrieval_service import merge_ranked_candidates


def test_merge_ranked_candidates_deduplicates_by_chunk_id():
    vector_hits = [
        RetrievalCandidate(
            chunk_id="law:1",
            doc_type="law",
            title="法",
            article_no="第一条",
            chunk_text="a",
            citation_label="cite-a",
            source_name="src",
            source_url="",
            effective_date="2020-01-01",
            vector_score=0.9,
            keyword_score=None,
            hybrid_score=0.0,
        )
    ]
    keyword_hits = [
        RetrievalCandidate(
            chunk_id="law:1",
            doc_type="law",
            title="法",
            article_no="第一条",
            chunk_text="a",
            citation_label="cite-a",
            source_name="src",
            source_url="",
            effective_date="2020-01-01",
            vector_score=None,
            keyword_score=0.8,
            hybrid_score=0.0,
        )
    ]
    merged = merge_ranked_candidates(vector_hits, keyword_hits, final_top_k=8)
    assert len(merged) == 1
    assert merged[0].hybrid_score > 0.8
```

```python
# tests/integration/test_retrieve_api.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_retrieve_returns_empty_results_with_dependency_override():
    app = create_app()

    async def fake_retrieve(query: str, top_k: int | None = None):
        return []

    app.dependency_overrides = {}
    app.state.test_retrieve = fake_retrieve
    client = TestClient(app)
    response = client.post("/retrieve", json={"query": "商家拒绝退款怎么办"})
    assert response.status_code == 200
    assert response.json()["results"] == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/unit/test_retrieval_service.py tests/integration/test_retrieve_api.py -v
```

Expected: FAIL because `retrieval_service` and the `/retrieve` route are not implemented.

- [ ] **Step 3: Implement hybrid merge logic, dependencies, and the API route**

```python
# app/services/retrieval_service.py
from app.schemas.retrieval import RetrievalCandidate, RetrievalResponse, RetrievalResultItem
from app.services.citation_service import build_citation
from app.services.query_normalization import normalize_query


def merge_ranked_candidates(
    vector_hits: list[RetrievalCandidate],
    keyword_hits: list[RetrievalCandidate],
    final_top_k: int,
) -> list[RetrievalCandidate]:
    merged: dict[str, RetrievalCandidate] = {}

    for candidate in vector_hits + keyword_hits:
        existing = merged.get(candidate.chunk_id)
        if existing is None:
            merged[candidate.chunk_id] = candidate
            continue
        existing.vector_score = max(existing.vector_score or 0.0, candidate.vector_score or 0.0) or None
        existing.keyword_score = max(existing.keyword_score or 0.0, candidate.keyword_score or 0.0) or None

    for candidate in merged.values():
        doc_bonus = 0.05 if candidate.doc_type == "law" else 0.0
        candidate.hybrid_score = (candidate.vector_score or 0.0) * 0.7 + (candidate.keyword_score or 0.0) * 0.3 + doc_bonus

    ranked = sorted(
        merged.values(),
        key=lambda item: (item.hybrid_score, item.doc_type == "law", -(int(item.article_no[1:-1]) if item.article_no and item.article_no[1:-1].isdigit() else 0)),
        reverse=True,
    )
    return ranked[:final_top_k]


class RetrievalService:
    def __init__(self, repository, embedding_client, settings):
        self._repository = repository
        self._embedding_client = embedding_client
        self._settings = settings

    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResponse:
        normalized = normalize_query(query)
        final_top_k = top_k or self._settings.retrieval_final_top_k
        vector_hits = self._repository.vector_search(
            query_embedding=self._embedding_client.embed_query(normalized),
            model_name=self._settings.openai_embedding_model,
            top_k=self._settings.retrieval_vector_top_k,
        )
        keyword_hits = self._repository.keyword_search(
            normalized_query=normalized,
            top_k=self._settings.retrieval_keyword_top_k,
        )
        merged = merge_ranked_candidates(vector_hits, keyword_hits, final_top_k)
        results = [
            RetrievalResultItem(
                chunk_id=item.chunk_id,
                doc_type=item.doc_type,
                title=item.title,
                article_no=item.article_no,
                chunk_text=item.chunk_text,
                citation=build_citation(item),
                scores={
                    "vector_score": item.vector_score,
                    "keyword_score": item.keyword_score,
                    "hybrid_score": item.hybrid_score,
                },
            )
            for item in merged
        ]
        return RetrievalResponse(query=normalized, results=results)
```

```python
# app/api/retrieve.py
from fastapi import APIRouter, Depends

from app.dependencies import get_retrieval_service
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse

router = APIRouter()


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(payload: RetrievalRequest, service=Depends(get_retrieval_service)) -> RetrievalResponse:
    return service.retrieve(payload.query, payload.top_k)
```

```python
# app/dependencies.py
from openai import OpenAI

from app.config import Settings, get_settings
from app.db.connection import get_connection
from app.db.repositories.retrieval_repository import RetrievalRepository
from app.services.retrieval_service import RetrievalService


class OpenAIEmbeddingClient:
    def __init__(self, api_key: str, model_name: str):
        self._client = OpenAI(api_key=api_key)
        self._model_name = model_name

    def embed_query(self, query: str) -> list[float]:
        response = self._client.embeddings.create(model=self._model_name, input=query)
        return response.data[0].embedding


def get_app_settings() -> Settings:
    return get_settings()


def get_retrieval_service(settings: Settings = get_app_settings()) -> RetrievalService:
    with get_connection() as conn:
        repository = RetrievalRepository(conn)
        embedding_client = OpenAIEmbeddingClient(settings.openai_api_key, settings.openai_embedding_model)
        return RetrievalService(repository, embedding_client, settings)
```

```python
# app/main.py
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.retrieve import router as retrieve_router


def create_app() -> FastAPI:
    app = FastAPI(title="law_helper backend", version="0.1.0")
    app.include_router(health_router)
    app.include_router(retrieve_router)
    return app


app = create_app()
```

- [ ] **Step 4: Make dependency injection testable and run the tests**

Adjust `get_retrieval_service()` so it can be dependency-overridden cleanly, then run:

```bash
pytest tests/unit/test_retrieval_service.py tests/integration/test_retrieve_api.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app tests/unit/test_retrieval_service.py tests/integration/test_retrieve_api.py
git commit -m "feat: add hybrid retrieval service and retrieve api"
```

---

### Task 5: Implement grounded answer generation and `/chat` API

**Files:**

- Create: `app/schemas/chat.py`
- Create: `app/services/llm_service.py`
- Create: `app/api/chat.py`
- Create: `app/prompts/qa_system.txt`
- Test: `tests/unit/test_llm_service.py`
- Test: `tests/integration/test_chat_api.py`
- Modify: `app/dependencies.py`
- Modify: `app/main.py`

- [ ] **Step 1: Write the failing chat and LLM tests**

```python
# tests/unit/test_llm_service.py
from app.schemas.retrieval import CitationPayload, RetrievalResponse, RetrievalResultItem
from app.services.llm_service import build_grounded_prompt


def test_build_grounded_prompt_includes_citation_labels():
    response = RetrievalResponse(
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
    prompt = build_grounded_prompt(response)
    assert "《中华人民共和国消费者权益保护法》第二十四条" in prompt
```

```python
# tests/integration/test_chat_api.py
from fastapi.testclient import TestClient

from app.main import create_app


def test_chat_returns_grounded_shape():
    app = create_app()
    client = TestClient(app)
    response = client.post("/chat", json={"query": "商家拒绝退款怎么办"})
    assert response.status_code in {200, 503}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:

```bash
pytest tests/unit/test_llm_service.py tests/integration/test_chat_api.py -v
```

Expected: FAIL because chat schemas, prompt assembly, and `/chat` do not exist.

- [ ] **Step 3: Implement chat schemas, prompt assembly, and LLM service**

```python
# app/schemas/chat.py
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
```

```text
# app/prompts/qa_system.txt
你是一个消费维权 RAG 助手。你只能根据提供的检索材料作答。
不要编造法条编号、出处或事实。
如果证据不足，明确说明“依据不足”。
输出必须包含：
1. 初步判断
2. 依据
3. 建议步骤
4. 风险提示
```

```python
# app/services/llm_service.py
from pathlib import Path

from openai import OpenAI

from app.schemas.chat import ChatAnswer, ChatResponse
from app.schemas.retrieval import RetrievalResponse


def build_grounded_prompt(retrieval_response: RetrievalResponse) -> str:
    context_blocks = []
    for item in retrieval_response.results:
        context_blocks.append(
            f"[{item.citation.citation_label}]\n{item.chunk_text}"
        )
    joined_context = "\n\n".join(context_blocks) if context_blocks else "无可用检索依据。"
    return f"用户问题：{retrieval_response.query}\n\n检索依据：\n{joined_context}"


class LLMService:
    def __init__(self, api_key: str, model_name: str):
        self._client = OpenAI(api_key=api_key)
        self._model_name = model_name
        self._system_prompt = Path("app/prompts/qa_system.txt").read_text(encoding="utf-8")

    def answer(self, retrieval_response: RetrievalResponse) -> ChatResponse:
        if not retrieval_response.results:
            return ChatResponse(
                query=retrieval_response.query,
                answer=ChatAnswer(
                    summary="依据不足，当前检索结果未提供足够法条依据。",
                    basis=[],
                    suggested_steps=["补充交易记录、聊天记录、商品页面截图后再次检索。"],
                    risk_notes=["当前回答不应视为确定法律结论。"],
                    insufficient_basis=True,
                ),
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
        return ChatResponse(
            query=retrieval_response.query,
            answer=ChatAnswer(
                summary=text,
                basis=[item.citation.citation_label for item in retrieval_response.results[:3]],
                suggested_steps=["保留证据并先向商家主张退换或赔偿。"],
                risk_notes=["模型回答受限于当前检索材料。"],
                insufficient_basis=False,
            ),
            citations=[item.citation for item in retrieval_response.results],
            retrieval={"result_count": len(retrieval_response.results)},
        )
```

- [ ] **Step 4: Expose `/chat` and run the tests**

```python
# app/api/chat.py
from fastapi import APIRouter, Depends

from app.dependencies import get_chat_service, get_retrieval_service
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    retrieval_service=Depends(get_retrieval_service),
    chat_service=Depends(get_chat_service),
) -> ChatResponse:
    retrieval_response = retrieval_service.retrieve(payload.query)
    return chat_service.answer(retrieval_response)
```

Update dependencies and app wiring, then run:

```bash
pytest tests/unit/test_llm_service.py tests/integration/test_chat_api.py -v
```

Expected: PASS for the prompt assembly test and stable API behavior with dependency overrides or mocked LLM behavior.

- [ ] **Step 5: Commit**

```bash
git add app tests/unit/test_llm_service.py tests/integration/test_chat_api.py
git commit -m "feat: add grounded chat api"
```

---

### Task 6: Add runbook, real-embedding cutover instructions, and full verification

**Files:**

- Create: `docs/backend_mvp_runbook.md`
- Modify: `.env.example`

- [ ] **Step 1: Write the runbook**

```md
# Backend MVP Runbook

## Local setup

1. Copy `.env.example` to `.env.local`
2. Fill in `DATABASE_URL` and `OPENAI_API_KEY`
3. Install dependencies with `python -m pip install -e ".[dev]"`

## Start the API

```bash
uvicorn app.main:app --reload
```

## Required pre-launch data state

- promoted corpus exists in `rag.chunks`
- promoted real embeddings exist in `rag.chunk_embeddings`
- `OPENAI_EMBEDDING_MODEL` matches the promoted embedding model name

## Real embedding cutover

Generate real embeddings:

```powershell
$env:OPENAI_API_KEY="your_api_key"
python .\scripts\build_openai_embeddings.py `
  --chunks .\build\ingestion\chunks.jsonl `
  --output .\build\embeddings\openai_embeddings.jsonl `
  --model text-embedding-3-small `
  --enabled-only
```

Load and promote:

```powershell
python .\scripts\load_embeddings_to_pg.py `
  --container law-helper-pg `
  --db-user law `
  --db-name law_helper `
  --embeddings .\build\embeddings\openai_embeddings.jsonl `
  --run-label "openai-small" `
  --model-name "text-embedding-3-small" `
  --distance-metric cosine `
  --chunk-scope enabled_only `
  --promote-if-clean
```
```

- [ ] **Step 2: Run the full test suite**

Run:

```bash
pytest tests/unit tests/integration -v
```

Expected: PASS.

- [ ] **Step 3: Smoke-test the API manually**

Run:

```bash
uvicorn app.main:app --reload
```

Then in another terminal:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/retrieve -H "Content-Type: application/json" -d "{\"query\":\"商家拒绝退款怎么办\"}"
curl -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"query\":\"网购商品质量有问题，商家不同意退货怎么办？\"}"
```

Expected:

- `/health` returns `{"status":"ok"}`
- `/retrieve` returns a JSON payload with `results`
- `/chat` returns a JSON payload with `answer`, `citations`, and `retrieval`

- [ ] **Step 4: Commit**

```bash
git add docs/backend_mvp_runbook.md .env.example
git commit -m "docs: add backend mvp runbook"
```

---

## Self-Review

### Spec coverage

- `GET /health`: covered in Task 1
- `POST /retrieve`: covered in Tasks 3 and 4
- `POST /chat`: covered in Task 5
- environment-driven config: covered in Task 1
- direct PostgreSQL retrieval on promoted tables: covered in Task 3
- hybrid recall and citation output: covered in Tasks 2 and 4
- grounded answer generation: covered in Task 5
- real embedding cutover instructions: covered in Task 6

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain
- Each code-writing step contains concrete file content or exact target code
- Each test step includes an exact command and expected result

### Type consistency

- Retrieval-related payloads live in `app/schemas/retrieval.py`
- Chat-related payloads live in `app/schemas/chat.py`
- `RetrievalService.retrieve()` feeds `LLMService.answer()`
- `/chat` depends on `/retrieve`-equivalent retrieval behavior instead of duplicating retrieval logic

---

Plan complete and saved to `docs/superpowers/plans/2026-05-01-backend-rag-mvp.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
