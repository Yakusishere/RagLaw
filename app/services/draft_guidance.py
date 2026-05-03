from dataclasses import dataclass

from app.schemas.draft import DraftTemplateType


@dataclass(frozen=True)
class DraftGuidance:
    missing_materials: list[str]
    next_steps: list[str]


KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    "订单页面": ("订单", "订单页面", "订单截图"),
    "支付记录": ("支付记录", "付款记录", "支付截图", "交易记录"),
    "聊天记录": ("聊天记录", "沟通记录", "协商记录", "客服聊天"),
    "商品问题照片或视频": ("问题照片", "商品问题照片", "照片", "图片", "视频", "录像"),
    "发票或收据": ("发票", "收据", "票据"),
    "平台售后或投诉记录": ("平台处理记录", "售后记录", "投诉记录", "平台客服"),
    "送达地址确认书": ("送达地址确认书",),
    "被告主体信息材料": ("统一社会信用代码", "工商登记", "营业执照", "企业信息"),
}


def build_draft_guidance(
    template_type: DraftTemplateType,
    facts: dict[str, str],
    missing_fields: list[str],
) -> DraftGuidance:
    missing_materials = _build_missing_materials(template_type, facts)
    next_steps = _build_next_steps(template_type, missing_fields, missing_materials)
    return DraftGuidance(
        missing_materials=missing_materials,
        next_steps=next_steps,
    )


def _build_missing_materials(
    template_type: DraftTemplateType,
    facts: dict[str, str],
) -> list[str]:
    if template_type == "complaint_letter":
        return _collect_template_materials(
            facts,
            fact_keys=("attachments_summary", "issue_details", "negotiation_history"),
            labels=(
                "订单页面",
                "支付记录",
                "聊天记录",
                "商品问题照片或视频",
                "发票或收据",
                "平台售后或投诉记录",
            ),
        )
    if template_type == "demand_letter":
        return _collect_template_materials(
            facts,
            fact_keys=("attachments_summary", "issue_summary", "breach_summary", "negotiation_history"),
            labels=(
                "订单页面",
                "支付记录",
                "聊天记录",
                "商品问题照片或视频",
                "平台售后或投诉记录",
            ),
        )
    return _build_lawsuit_missing_materials(facts)


def _build_lawsuit_missing_materials(facts: dict[str, str]) -> list[str]:
    materials = _collect_template_materials(
        facts,
        fact_keys=("evidence_list",),
        labels=(
            "订单页面",
            "支付记录",
            "聊天记录",
            "商品问题照片或视频",
            "发票或收据",
            "平台售后或投诉记录",
            "送达地址确认书",
        ),
    )

    if not facts.get("plaintiff_id_no", "").strip():
        materials.insert(0, "原告身份证明材料")

    defendant_type = facts.get("defendant_type", "").strip()
    evidence_text = _join_fact_text(facts, ("evidence_list",))
    if _looks_like_company_defendant(defendant_type) and not _has_keywords(
        evidence_text,
        KEYWORD_GROUPS["被告主体信息材料"],
    ):
        materials.append("被告主体信息材料")

    return _dedupe_preserving_order(materials)


def _collect_template_materials(
    facts: dict[str, str],
    *,
    fact_keys: tuple[str, ...],
    labels: tuple[str, ...],
) -> list[str]:
    haystack = _join_fact_text(facts, fact_keys)
    missing: list[str] = []
    for label in labels:
        if not _has_keywords(haystack, KEYWORD_GROUPS[label]):
            missing.append(label)
    return missing


def _join_fact_text(facts: dict[str, str], fact_keys: tuple[str, ...]) -> str:
    return "\n".join(facts.get(key, "").strip() for key in fact_keys if facts.get(key, "").strip())


def _has_keywords(text: str, keywords: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(keyword.lower() in lowered for keyword in keywords)


def _looks_like_company_defendant(defendant_type: str) -> bool:
    return any(flag in defendant_type for flag in ("公司", "商家", "企业", "平台"))


def _dedupe_preserving_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _build_next_steps(
    template_type: DraftTemplateType,
    missing_fields: list[str],
    missing_materials: list[str],
) -> list[str]:
    steps: list[str] = []
    if missing_fields:
        steps.append("请先补全必填字段后再重新生成或核对文书。")
    if missing_materials:
        steps.append(f"优先补齐以下材料：{'、'.join(missing_materials)}。")

    if template_type == "complaint_letter":
        steps.extend(
            [
                "核对投诉对象、事实经过、具体诉求和处理期限是否准确。",
                "先向商家或平台提交投诉信并保留提交记录。",
                "如仍未解决，可转入 12315 投诉或行政调解，并关注 7 个工作日处理告知与 60 日调解期限。",
            ]
        )
    elif template_type == "demand_letter":
        steps.extend(
            [
                "核对催告事项、金额和履行期限后，以可留痕方式向商家送达催告函。",
                "保存送达凭证，逾期未履行时再转入投诉、调解或诉讼程序。",
                "继续补强订单、支付、沟通和商品问题证据。",
            ]
        )
    else:
        steps.extend(
            [
                "核对受理法院、案由、诉讼请求与事实理由是否准确。",
                "整理身份材料、被告主体信息、证据目录和送达地址确认书后再提交立案。",
                "通过人民法院在线服务填写当事人信息并上传材料，提交后关注 7 日内是否立案或补正。",
            ]
        )
    return steps
