from app.services.draft_guidance import build_draft_guidance


def test_complaint_letter_guidance_reports_missing_core_evidence_materials():
    guidance = build_draft_guidance(
        template_type="complaint_letter",
        facts={
            "consumer_name": "张三",
            "merchant_name": "某商家",
            "issue_details": "耳机存在杂音",
            "negotiation_history": "和商家沟通过两次",
            "attachments_summary": "仅附商品照片",
        },
        missing_fields=[],
    )

    assert "订单页面" in guidance.missing_materials
    assert "支付记录" in guidance.missing_materials
    assert guidance.next_steps[0].startswith("优先补齐以下材料：")


def test_lawsuit_guidance_reports_identity_and_service_materials_when_not_reflected():
    guidance = build_draft_guidance(
        template_type="lawsuit_draft",
        facts={
            "defendant_type": "公司",
            "evidence_list": "订单页面、聊天记录、商品照片",
        },
        missing_fields=[],
    )

    assert "原告身份证明材料" in guidance.missing_materials
    assert "被告主体信息材料" in guidance.missing_materials
    assert "送达地址确认书" in guidance.missing_materials


def test_missing_fields_always_take_priority_in_next_steps():
    guidance = build_draft_guidance(
        template_type="demand_letter",
        facts={"attachments_summary": "订单页面、支付截图"},
        missing_fields=["receiver_name"],
    )

    assert guidance.next_steps[0] == "请先补全必填字段后再重新生成或核对文书。"


def test_keyword_hit_prevents_duplicate_material_warning():
    guidance = build_draft_guidance(
        template_type="complaint_letter",
        facts={
            "attachments_summary": "订单页面、支付记录、聊天记录、商品问题照片、发票、平台处理记录",
            "issue_details": "商品有质量问题",
            "negotiation_history": "已联系平台客服",
        },
        missing_fields=[],
    )

    assert guidance.missing_materials == []
