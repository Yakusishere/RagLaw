from pydantic import ValidationError

from app.schemas.draft import (
    DraftRequest,
    DraftResponse,
    DraftTemplateFieldResponse,
    DraftTemplateListResponse,
    DraftTemplateMetadataResponse,
)


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


def test_draft_response_supports_missing_fields_materials_and_citations():
    response = DraftResponse(
        template_type="complaint_letter",
        template_name="投诉信（商品质量纠纷）",
        draft_text="投诉信正文",
        missing_fields=["merchant_name"],
        missing_materials=["订单页面"],
        cited_laws=["《中华人民共和国消费者权益保护法》第二十四条"],
        next_steps=["补充商家名称后重新生成。"],
    )
    assert response.missing_fields == ["merchant_name"]
    assert response.missing_materials == ["订单页面"]
    assert response.cited_laws[0].endswith("第二十四条")


def test_draft_response_rejects_unknown_template_type():
    try:
        DraftResponse(
            template_type="unknown",
            template_name="投诉信（商品质量纠纷）",
            draft_text="投诉信正文",
            missing_fields=[],
            missing_materials=[],
            cited_laws=[],
            next_steps=[],
        )
    except ValidationError as exc:
        assert "template_type" in str(exc)
    else:
        raise AssertionError("expected ValidationError")


def test_draft_template_metadata_response_supports_field_lists():
    response = DraftTemplateMetadataResponse(
        template_type="complaint_letter",
        template_name="投诉信（商品质量纠纷）",
        required_fields=[
            DraftTemplateFieldResponse(
                name="consumer_name",
                label="投诉人姓名",
                type="string",
            )
        ],
        optional_fields=[
            DraftTemplateFieldResponse(
                name="consumer_id_no",
                label="投诉人证件号",
                type="string",
            )
        ],
    )

    assert response.required_fields[0].name == "consumer_name"
    assert response.optional_fields[0].label == "投诉人证件号"


def test_draft_template_list_response_wraps_templates():
    response = DraftTemplateListResponse(
        templates=[
            DraftTemplateMetadataResponse(
                template_type="complaint_letter",
                template_name="投诉信（商品质量纠纷）",
                required_fields=[],
                optional_fields=[],
            ),
            DraftTemplateMetadataResponse(
                template_type="demand_letter",
                template_name="催告函（退款退货）",
                required_fields=[],
                optional_fields=[],
            ),
        ]
    )

    assert len(response.templates) == 2
    assert response.templates[1].template_type == "demand_letter"
