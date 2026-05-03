from app.schemas.draft import DraftRequest
from app.schemas.retrieval import CitationPayload, RetrievalResponse, RetrievalResultItem
from app.services.draft_service import DraftService


def build_retrieval_response() -> RetrievalResponse:
    return RetrievalResponse(
        query="投诉信 商品质量纠纷 张三 某商家 蓝牙耳机",
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


class StubTemplateService:
    def get_template(self, template_type: str):
        assert template_type == "complaint_letter"
        return type(
            "Template",
            (),
            {
                "template_type": "complaint_letter",
                "template_name": "投诉信（商品质量纠纷）",
                "required_fields": [
                    type("Field", (), {"name": "consumer_name"})(),
                    type("Field", (), {"name": "merchant_name"})(),
                ],
                "template_text": "投诉人：{{consumer_name}}\n商家：{{merchant_name}}",
                "suggested_citations": ["《中华人民共和国消费者权益保护法》第二十四条"],
            },
        )()


class StubRetrievalService:
    def __init__(self):
        self.calls: list[tuple[str, int | None]] = []

    def retrieve(self, query: str, top_k: int | None = None):
        self.calls.append((query, top_k))
        return build_retrieval_response()


class StubLLMService:
    def __init__(self):
        self.calls: list[dict[str, object]] = []

    def draft_document(self, *, template_text: str, facts: dict[str, str], retrieval_response):
        self.calls.append(
            {
                "template_text": template_text,
                "facts": facts,
                "retrieval_response": retrieval_response,
            }
        )
        return "投诉人：张三\n商家：某商家"


def test_draft_service_returns_missing_fields_without_calling_llm():
    retrieval_service = StubRetrievalService()
    llm_service = StubLLMService()
    service = DraftService(StubTemplateService(), retrieval_service, llm_service)

    response = service.generate(
        DraftRequest(
            template_type="complaint_letter",
            facts={"consumer_name": "张三"},
        )
    )

    assert response.template_name == "投诉信（商品质量纠纷）"
    assert response.missing_fields == ["merchant_name"]
    assert response.draft_text == ""
    assert response.cited_laws == []
    assert retrieval_service.calls == []
    assert llm_service.calls == []


def test_draft_service_renders_when_required_fields_are_complete():
    retrieval_service = StubRetrievalService()
    llm_service = StubLLMService()
    service = DraftService(StubTemplateService(), retrieval_service, llm_service)

    response = service.generate(
        DraftRequest(
            template_type="complaint_letter",
            facts={"consumer_name": "张三", "merchant_name": "某商家"},
        )
    )

    assert response.missing_fields == []
    assert response.draft_text == "投诉人：张三\n商家：某商家"
    assert response.cited_laws == ["《中华人民共和国消费者权益保护法》第二十四条"]
    assert response.next_steps == ["核对文书内容并补齐证据附件后再正式提交。"]
    assert retrieval_service.calls == [("投诉信（商品质量纠纷） 张三 某商家", None)]
    assert llm_service.calls
