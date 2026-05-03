from pathlib import Path

from app.schemas.chat import ChatStreamEvent
from app.schemas.retrieval import CitationPayload, RetrievalResponse, RetrievalResultItem
from app.services.llm_service import (
    LLMService,
    build_drafting_prompt,
    build_grounded_prompt,
)


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
    def __init__(
        self,
        events=None,
        exc: Exception | None = None,
        create_text: str = "默认回答",
        create_exc: Exception | None = None,
    ):
        self._events = events or []
        self._exc = exc
        self._create_text = create_text
        self._create_exc = create_exc
        self.create_calls: list[dict[str, object]] = []

    def stream(self, **kwargs):
        if self._exc is not None:
            raise self._exc
        return FakeStream(self._events)

    def create(self, **kwargs):
        self.create_calls.append(kwargs)
        if self._create_exc is not None:
            raise self._create_exc
        return type("FakeCreateResponse", (), {"output_text": self._create_text})()


class FakeOpenAIClient:
    def __init__(
        self,
        events=None,
        exc: Exception | None = None,
        create_text: str = "默认回答",
        create_exc: Exception | None = None,
    ):
        self.responses = FakeResponsesAPI(
            events=events,
            exc=exc,
            create_text=create_text,
            create_exc=create_exc,
        )


def test_build_grounded_prompt_includes_citation_labels():
    response = build_retrieval_response()

    prompt = build_grounded_prompt(response)

    assert "《中华人民共和国消费者权益保护法》第二十四条" in prompt


def test_build_drafting_prompt_includes_template_facts_and_citations():
    response = build_retrieval_response()

    prompt = build_drafting_prompt(
        template_text="投诉人：{{consumer_name}}",
        facts={"consumer_name": "张三", "merchant_name": "某商家"},
        retrieval_response=response,
    )

    assert "模板正文：" in prompt
    assert "投诉人：{{consumer_name}}" in prompt
    assert "- consumer_name: 张三" in prompt
    assert "- merchant_name: 某商家" in prompt
    assert "《中华人民共和国消费者权益保护法》第二十四条" in prompt


def test_llm_service_loads_prompt_relative_to_module(monkeypatch):
    monkeypatch.chdir(Path(__file__).resolve().parent)

    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=FakeOpenAIClient(),
    )

    assert service._system_prompt


def test_answer_returns_supported_chat_response():
    client = FakeOpenAIClient(create_text="根据现有检索材料，可以主张退款。")
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=client,
    )

    response = service.answer(build_retrieval_response())

    assert response.query == "商家拒绝退款怎么办"
    assert response.answer.summary == "根据现有检索材料，可以主张退款。"
    assert response.answer.basis == ["《中华人民共和国消费者权益保护法》第二十四条"]
    assert response.answer.insufficient_basis is False
    assert response.retrieval == {"result_count": 1}
    assert len(response.citations) == 1
    assert client.responses.create_calls


def test_draft_document_returns_rendered_text():
    client = FakeOpenAIClient(create_text="投诉信正文")
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=client,
    )

    draft_text = service.draft_document(
        template_text="投诉人：{{consumer_name}}",
        facts={"consumer_name": "张三", "merchant_name": "某商家"},
        retrieval_response=build_retrieval_response(),
    )

    assert draft_text == "投诉信正文"
    assert client.responses.create_calls


def test_draft_document_normalizes_upstream_create_failure():
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=FakeOpenAIClient(create_exc=ValueError("boom")),
    )

    try:
        service.draft_document(
            template_text="投诉人：{{consumer_name}}",
            facts={"consumer_name": "张三"},
            retrieval_response=build_retrieval_response(),
        )
        assert False, "expected draft_document() to raise RuntimeError"
    except RuntimeError as exc:
        assert str(exc) == "上游模型调用失败"
        assert isinstance(exc.__cause__, ValueError)
        assert str(exc.__cause__) == "boom"


def test_answer_returns_insufficient_basis_without_upstream_call():
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=FakeOpenAIClient(create_exc=AssertionError("should not call upstream")),
    )

    response = service.answer(RetrievalResponse(query="证据不足怎么办", results=[]))

    assert response.query == "证据不足怎么办"
    assert response.answer.summary == "依据不足，当前检索结果未提供足够法条依据。"
    assert response.answer.insufficient_basis is True
    assert response.citations == []
    assert response.retrieval == {"result_count": 0}


def test_answer_normalizes_upstream_create_failure():
    service = LLMService(
        api_key="test-key",
        model_name="test-model",
        client=FakeOpenAIClient(create_exc=ValueError("boom")),
    )

    try:
        service.answer(build_retrieval_response())
        assert False, "expected answer() to raise RuntimeError"
    except RuntimeError as exc:
        assert str(exc) == "上游模型调用失败"
        assert isinstance(exc.__cause__, ValueError)
        assert str(exc.__cause__) == "boom"


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

    assert all(isinstance(event, ChatStreamEvent) for event in events)
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
    assert events[1].data["message"] == "上游模型调用失败"
