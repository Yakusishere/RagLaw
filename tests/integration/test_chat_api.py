import json

from fastapi.testclient import TestClient

from app.dependencies import get_chat_service, get_retrieval_service
from app.main import create_app
from app.schemas.chat import ChatAnswer, ChatResponse, ChatStreamEvent
from app.schemas.retrieval import CitationPayload, RetrievalResponse, RetrievalResultItem
from app.services.exceptions import UpstreamDependencyError


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
                "citations": [retrieval_response.results[0].citation],
                "retrieval": {"result_count": 1},
                "basis": ["《中华人民共和国消费者权益保护法》第二十四条"],
                "insufficient_basis": False,
                "suggested_steps": ["先与商家协商并保留证据。"],
                "risk_notes": ["若证据不足，主张效果会受影响。"],
            },
        )
        yield ChatStreamEvent(event="done", data={"ok": True})


class FakeFailingChatService:
    def answer(self, retrieval_response: RetrievalResponse) -> ChatResponse:
        raise UpstreamDependencyError()

    def stream_answer(self, retrieval_response: RetrievalResponse):
        yield ChatStreamEvent(event="meta", data={"query": retrieval_response.query})
        yield ChatStreamEvent(event="error", data={"message": "上游模型调用失败"})


class FakeFailingRetrievalService:
    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResponse:
        raise UpstreamDependencyError()


def collect_stream_frames(client: TestClient, query: str) -> tuple[object, list[str]]:
    with client.stream("POST", "/chat/stream", json={"query": query}) as response:
        chunks = list(response.iter_text())
        body = "".join(chunks)
        frames = [frame for frame in body.split("\n\n") if frame]
        return response, frames


def parse_frame(frame: str) -> tuple[str, dict]:
    lines = frame.splitlines()
    assert len(lines) == 2
    assert lines[0].startswith("event: ")
    assert lines[1].startswith("data: ")
    return lines[0][7:], json.loads(lines[1][6:])


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


def test_chat_returns_502_when_upstream_model_call_fails():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeRetrievalService()
    app.dependency_overrides[get_chat_service] = lambda: FakeFailingChatService()

    client = TestClient(app)
    response = client.post("/chat", json={"query": "商家拒绝退款怎么办"})

    assert response.status_code == 502
    assert response.json() == {"detail": "上游依赖调用失败"}


def test_chat_returns_502_when_retrieval_upstream_call_fails():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeFailingRetrievalService()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    client = TestClient(app)
    response = client.post("/chat", json={"query": "商家拒绝退款怎么办"})

    assert response.status_code == 502
    assert response.json() == {"detail": "上游依赖调用失败"}


def test_chat_stream_returns_sse_frames():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeRetrievalService()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    client = TestClient(app)
    response, frames = collect_stream_frames(client, "商家拒绝退款怎么办")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [parse_frame(frame)[0] for frame in frames] == ["meta", "delta", "citations", "done"]
    assert frames[0] == 'event: meta\ndata: {"query":"商家拒绝退款怎么办"}'
    assert frames[-1] == 'event: done\ndata: {"ok":true}'

    citations_payload = parse_frame(frames[2])[1]
    assert citations_payload["citations"][0]["citation_label"] == "《中华人民共和国消费者权益保护法》第二十四条"
    assert citations_payload["retrieval"]["result_count"] == 1


def test_chat_stream_emits_error_event_when_stream_setup_fails():
    app = create_app()
    app.dependency_overrides[get_retrieval_service] = lambda: FakeFailingRetrievalService()
    app.dependency_overrides[get_chat_service] = lambda: FakeChatService()

    client = TestClient(app)
    response, frames = collect_stream_frames(client, "商家拒绝退款怎么办")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert [parse_frame(frame)[0] for frame in frames] == ["error"]
    assert parse_frame(frames[0])[1]["message"] == "上游依赖调用失败"
