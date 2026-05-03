from app.schemas.draft import (
    DraftRequest,
    DraftTemplate,
    DraftTemplateDerivedPlaceholder,
    DraftTemplateField,
)
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


class DemandLetterTemplateService:
    def get_template(self, template_type: str):
        assert template_type == "demand_letter"
        return DraftTemplate(
            template_id="demand_letter_refund_return_v1",
            template_name="催告函（退款退货）",
            doc_type="template",
            template_type="demand_letter",
            scene="refund_return_dispute",
            status="draft_ready",
            required_fields=[
                DraftTemplateField(name="sender_name", label="发函人姓名", type="string"),
                DraftTemplateField(name="sender_contact", label="发函人联系方式", type="string"),
                DraftTemplateField(name="receiver_name", label="收函商家名称", type="string"),
                DraftTemplateField(
                    name="receiver_address_or_contact",
                    label="收函商家联系方式或地址",
                    type="string",
                ),
                DraftTemplateField(name="platform_name", label="交易平台名称", type="string"),
                DraftTemplateField(name="product_name", label="商品名称", type="string"),
                DraftTemplateField(name="order_no", label="订单号", type="string"),
                DraftTemplateField(name="transaction_time", label="交易时间", type="string"),
                DraftTemplateField(name="payment_amount", label="支付金额", type="string"),
                DraftTemplateField(name="issue_summary", label="问题摘要", type="text"),
                DraftTemplateField(name="breach_summary", label="违约或拒绝履行情况", type="text"),
                DraftTemplateField(name="negotiation_history", label="协商经过", type="text"),
                DraftTemplateField(name="demand_items", label="催告事项", type="text"),
                DraftTemplateField(name="deadline_days", label="履行期限（天）", type="integer"),
                DraftTemplateField(name="letter_date", label="发函日期", type="string"),
            ],
            optional_fields=[
                DraftTemplateField(name="sender_id_no", label="发函人证件号", type="string"),
                DraftTemplateField(name="payment_account", label="收款账户", type="text"),
                DraftTemplateField(name="attachments_summary", label="附件清单", type="text"),
                DraftTemplateField(name="legal_basis", label="自定义依据说明", type="text"),
            ],
            derived_placeholders=[
                DraftTemplateDerivedPlaceholder.model_validate(
                    {
                        "name": "sender_id_block",
                        "from": ["sender_id_no"],
                        "rule": "有值时渲染为“证件号：...”，无值时置空",
                    }
                ),
                DraftTemplateDerivedPlaceholder.model_validate(
                    {
                        "name": "payment_account_block",
                        "from": ["payment_account"],
                        "rule": "有值时渲染为收款账户段，无值时置空",
                    }
                ),
                DraftTemplateDerivedPlaceholder.model_validate(
                    {
                        "name": "attachments_block",
                        "from": ["attachments_summary"],
                        "rule": "有值时渲染为附件清单段，无值时置空",
                    }
                ),
                DraftTemplateDerivedPlaceholder.model_validate(
                    {
                        "name": "legal_basis_or_default",
                        "from": ["legal_basis"],
                        "rule": "优先使用 legal_basis；缺失时使用模板默认依据段",
                    }
                ),
            ],
            template_text=(
                "催告函\n\n"
                "致：{{receiver_name}}\n"
                "联系方式/地址：{{receiver_address_or_contact}}\n"
                "平台名称：{{platform_name}}\n\n"
                "发函人：{{sender_name}}\n"
                "联系方式：{{sender_contact}}\n"
                "{{sender_id_block}}\n\n"
                "鉴于本人于 {{transaction_time}} 购买 {{product_name}}，订单号为 {{order_no}}，"
                "实付金额为人民币 {{payment_amount}} 元。交易完成后出现如下问题：{{issue_summary}}。\n\n"
                "截至本函出具之日，您方存在以下未妥善履行义务的情形：\n"
                "{{breach_summary}}\n\n"
                "本人此前已通过 {{negotiation_history}} 与您方沟通处理，但问题至今未解决。\n\n"
                "依据说明：\n{{legal_basis_or_default}}\n\n"
                "现正式催告如下：\n{{demand_items}}\n\n"
                "请贵方于收到本函后 {{deadline_days}} 日内完成处理。{{payment_account_block}}\n\n"
                "如逾期未履行，本人将依法继续采取投诉、举报、申请调解、提起诉讼等措施，并主张因此产生的合理维权成本。\n\n"
                "{{attachments_block}}\n\n"
                "发函人：{{sender_name}}\n"
                "日期：{{letter_date}}"
            ),
        )


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
    assert response.missing_materials == [
        "订单页面",
        "支付记录",
        "聊天记录",
        "商品问题照片或视频",
        "发票或收据",
        "平台售后或投诉记录",
    ]
    assert response.draft_text == ""
    assert response.cited_laws == []
    assert response.next_steps[0] == "请先补全必填字段后再重新生成或核对文书。"
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
    assert response.missing_materials == [
        "订单页面",
        "支付记录",
        "聊天记录",
        "商品问题照片或视频",
        "发票或收据",
        "平台售后或投诉记录",
    ]
    assert response.draft_text == "投诉人：张三\n商家：某商家"
    assert response.cited_laws == ["《中华人民共和国消费者权益保护法》第二十四条"]
    assert response.next_steps == [
        "优先补齐以下材料：订单页面、支付记录、聊天记录、商品问题照片或视频、发票或收据、平台售后或投诉记录。",
        "核对投诉对象、事实经过、具体诉求和处理期限是否准确。",
        "先向商家或平台提交投诉信并保留提交记录。",
        "如仍未解决，可转入 12315 投诉或行政调解，并关注 7 个工作日处理告知与 60 日调解期限。",
    ]
    assert retrieval_service.calls == [("投诉信（商品质量纠纷） 张三 某商家", None)]
    assert llm_service.calls


def test_draft_service_renders_template_text_before_calling_llm():
    retrieval_service = StubRetrievalService()
    llm_service = StubLLMService()
    service = DraftService(DemandLetterTemplateService(), retrieval_service, llm_service)

    service.generate(
        DraftRequest(
            template_type="demand_letter",
            facts={
                "sender_name": "张三",
                "sender_contact": "13800000000",
                "receiver_name": "某商家",
                "receiver_address_or_contact": "北京市朝阳区某路1号",
                "platform_name": "某电商平台",
                "product_name": "蓝牙耳机",
                "order_no": "ORDER-20260503-002",
                "transaction_time": "2026-04-18",
                "payment_amount": "399",
                "issue_summary": "商品存在质量问题，商家拒绝退货退款",
                "breach_summary": "商家拒绝处理退货退款申请",
                "negotiation_history": "平台客服和商家客服沟通",
                "demand_items": "退还货款并承担退货运费",
                "deadline_days": "7",
                "letter_date": "2026-05-03",
            },
        )
    )

    rendered_template = llm_service.calls[0]["template_text"]
    assert "{{" not in rendered_template
    assert "发函人：张三" in rendered_template
    assert "联系方式：13800000000" in rendered_template
    assert "证件号：" not in rendered_template
    assert "请贵方于收到本函后 7 日内完成处理。" in rendered_template
