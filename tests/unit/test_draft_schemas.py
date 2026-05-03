from pydantic import ValidationError

from app.schemas.draft import DraftRequest, DraftResponse


def test_draft_request_accepts_template_type_and_optional_facts():
    request = DraftRequest(
        template_type="complaint_letter",
        facts={"consumer_name": "张三", "product_name": "耳机"},
    )
    assert request.template_type == "complaint_letter"
    assert request.facts["consumer_name"] == "张三"
    assert DraftRequest(template_type="complaint_letter").facts == {}


def test_draft_request_rejects_unknown_template_type():
    try:
        DraftRequest(template_type="unknown", facts={})
    except ValidationError as exc:
        assert "template_type" in str(exc)
    else:
        raise AssertionError("expected ValidationError")


def test_draft_response_supports_missing_fields_and_citations():
    response = DraftResponse(
        template_type="complaint_letter",
        template_name="投诉信（商品质量纠纷）",
        draft_text="投诉信正文",
        missing_fields=["merchant_name"],
        cited_laws=["《中华人民共和国消费者权益保护法》第二十四条"],
        next_steps=["补充商家名称后重新生成。"],
    )
    assert response.missing_fields == ["merchant_name"]
    assert response.cited_laws[0].endswith("第二十四条")


def test_draft_response_rejects_unknown_template_type():
    try:
        DraftResponse(
            template_type="unknown",
            template_name="投诉信（商品质量纠纷）",
            draft_text="投诉信正文",
            missing_fields=[],
            cited_laws=[],
            next_steps=[],
        )
    except ValidationError as exc:
        assert "template_type" in str(exc)
    else:
        raise AssertionError("expected ValidationError")
