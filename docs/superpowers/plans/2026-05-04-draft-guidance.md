# Draft Guidance Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic `next_steps` guidance and `missing_materials` output to `POST /draft`, then verify the behavior with unit tests, integration tests, and real API calls.

**Architecture:** Introduce a dedicated pure-Python guidance module that owns template-specific material checks and step generation. Keep `DraftService` as the orchestration layer: it still loads templates, validates facts, retrieves authorities, and calls the LLM, but now delegates post-processing guidance generation to the new module before returning `DraftResponse`.

**Tech Stack:** FastAPI, Pydantic, pytest, file-backed template metadata, existing OpenAI-backed draft generation flow.

---

## File Structure

- `app/schemas/draft.py`
  - Extend `DraftResponse` with `missing_materials`.
- `app/services/draft_guidance.py`
  - New pure rule module for deterministic material detection and `next_steps`.
- `app/services/draft_service.py`
  - Integrate the new guidance module into the existing `/draft` flow.
- `tests/unit/test_draft_schemas.py`
  - Update response schema tests for the new field.
- `tests/unit/test_draft_guidance.py`
  - New unit tests for template-specific missing-material and step-generation rules.
- `tests/unit/test_draft_service.py`
  - Update orchestration tests to assert guidance generation in missing-field and complete-field cases.
- `tests/integration/test_draft_api.py`
  - Update `/draft` API contract tests for the new response shape and template-specific behavior.
- `docs/frontend_api_contract.md`
  - Document the new field and revised `/draft` examples.

### Task 1: Add Draft Guidance Rules Module

**Files:**
- Create: `app/services/draft_guidance.py`
- Test: `tests/unit/test_draft_guidance.py`

- [ ] **Step 1: Write the failing unit tests for deterministic guidance rules**

```python
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
```

- [ ] **Step 2: Run the new guidance tests and confirm they fail**

Run: `PYTHONPATH=. python -m pytest tests/unit/test_draft_guidance.py -q`  
Expected: FAIL with `ModuleNotFoundError` for `app.services.draft_guidance` or missing `build_draft_guidance`.

- [ ] **Step 3: Implement the new guidance module with stable rule tables**

```python
from dataclasses import dataclass
from typing import Literal

from app.schemas.draft import DraftTemplateType


@dataclass(frozen=True)
class DraftGuidance:
    missing_materials: list[str]
    next_steps: list[str]


def build_draft_guidance(
    template_type: DraftTemplateType,
    facts: dict[str, str],
    missing_fields: list[str],
) -> DraftGuidance:
    materials = _build_missing_materials(template_type, facts)
    return DraftGuidance(
        missing_materials=materials,
        next_steps=_build_next_steps(template_type, missing_fields, materials),
    )
```

```python
KEYWORD_GROUPS = {
    "订单页面": ("订单", "订单页面", "订单截图"),
    "支付记录": ("支付记录", "付款记录", "支付截图", "交易记录"),
    "聊天记录": ("聊天记录", "沟通记录", "协商记录", "客服聊天"),
    "商品问题照片或视频": ("照片", "图片", "视频", "开箱视频", "问题照片"),
    "发票或收据": ("发票", "收据", "票据"),
    "平台售后或投诉记录": ("平台处理记录", "售后记录", "投诉记录", "平台客服"),
    "送达地址确认书": ("送达地址确认书",),
    "被告主体信息材料": ("统一社会信用代码", "工商登记", "营业执照", "企业信息"),
}


def _build_missing_materials(template_type: DraftTemplateType, facts: dict[str, str]) -> list[str]:
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
```

```python
def _build_next_steps(
    template_type: DraftTemplateType,
    missing_fields: list[str],
    missing_materials: list[str],
) -> list[str]:
    steps: list[str] = []
    if missing_fields:
        steps.append("请先补全必填字段后再重新生成或核对文书。")
    if missing_materials:
        joined = "、".join(missing_materials)
        steps.append(f"优先补齐以下材料：{joined}。")
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
```

- [ ] **Step 4: Run the guidance unit tests and confirm they pass**

Run: `PYTHONPATH=. python -m pytest tests/unit/test_draft_guidance.py -q`  
Expected: PASS

- [ ] **Step 5: Commit the guidance module**

```bash
git add app/services/draft_guidance.py tests/unit/test_draft_guidance.py
git commit -m "feat: add deterministic draft guidance rules"
```

### Task 2: Integrate Guidance Into `/draft` Response Flow

**Files:**
- Modify: `app/schemas/draft.py`
- Modify: `app/services/draft_service.py`
- Modify: `tests/unit/test_draft_schemas.py`
- Modify: `tests/unit/test_draft_service.py`
- Modify: `tests/integration/test_draft_api.py`

- [ ] **Step 1: Extend tests to expect `missing_materials` in schema, service, and API responses**

```python
def test_draft_response_supports_missing_fields_materials_and_citations():
    response = DraftResponse(
        template_type="complaint_letter",
        template_name="投诉信（商品质量纠纷）",
        draft_text="投诉信正文",
        missing_fields=["merchant_name"],
        missing_materials=["订单页面"],
        cited_laws=["《中华人民共和国消费者权益保护法》第二十四条"],
        next_steps=["请先补全必填字段后再重新生成或核对文书。"],
    )

    assert response.missing_materials == ["订单页面"]
```

```python
def test_draft_service_returns_missing_fields_without_calling_llm():
    ...
    assert response.missing_materials == [
        "订单页面",
        "支付记录",
        "聊天记录",
        "商品问题照片或视频",
        "发票或收据",
        "平台售后或投诉记录",
    ]
    assert response.next_steps[0] == "请先补全必填字段后再重新生成或核对文书。"
```

```python
def test_post_draft_response_shape_is_stable():
    ...
    assert sorted(body.keys()) == [
        "cited_laws",
        "draft_text",
        "missing_fields",
        "missing_materials",
        "next_steps",
        "template_name",
        "template_type",
    ]
```

- [ ] **Step 2: Run targeted tests and confirm they fail on the missing field**

Run: `PYTHONPATH=. python -m pytest tests/unit/test_draft_schemas.py tests/unit/test_draft_service.py tests/integration/test_draft_api.py -q`  
Expected: FAIL because `DraftResponse` does not yet define `missing_materials` and existing response payloads are missing the new key.

- [ ] **Step 3: Implement schema and service integration**

```python
# app/schemas/draft.py
class DraftResponse(BaseModel):
    template_type: DraftTemplateType
    template_name: str
    draft_text: str
    missing_fields: list[str]
    missing_materials: list[str]
    cited_laws: list[str]
    next_steps: list[str]
```

```python
# app/services/draft_service.py
from app.services.draft_guidance import build_draft_guidance


class DraftService:
    ...
    def generate(self, request: DraftRequest) -> DraftResponse:
        template = self._template_service.get_template(request.template_type)
        missing_fields = build_missing_fields(template.required_fields, request.facts)
        guidance = build_draft_guidance(
            template_type=request.template_type,
            facts=request.facts,
            missing_fields=missing_fields,
        )

        if missing_fields:
            return DraftResponse(
                template_type=request.template_type,
                template_name=template.template_name,
                draft_text="",
                missing_fields=missing_fields,
                missing_materials=guidance.missing_materials,
                cited_laws=[],
                next_steps=guidance.next_steps,
            )
```

```python
        return DraftResponse(
            template_type=request.template_type,
            template_name=template.template_name,
            draft_text=draft_text,
            missing_fields=[],
            missing_materials=guidance.missing_materials,
            cited_laws=[
                item.citation.citation_label for item in retrieval_response.results[:5]
            ],
            next_steps=guidance.next_steps,
        )
```

- [ ] **Step 4: Run targeted tests again and confirm they pass**

Run: `PYTHONPATH=. python -m pytest tests/unit/test_draft_schemas.py tests/unit/test_draft_guidance.py tests/unit/test_draft_service.py tests/integration/test_draft_api.py -q`  
Expected: PASS

- [ ] **Step 5: Commit the `/draft` integration changes**

```bash
git add app/schemas/draft.py app/services/draft_service.py tests/unit/test_draft_schemas.py tests/unit/test_draft_service.py tests/integration/test_draft_api.py
git commit -m "feat: add draft missing materials guidance"
```

### Task 3: Update Frontend Contract and Run Real Verification

**Files:**
- Modify: `docs/frontend_api_contract.md`

- [ ] **Step 1: Update the frontend API contract for the new `/draft` field and examples**

```md
type DraftResponse = {
  template_type: "complaint_letter" | "demand_letter" | "lawsuit_draft"
  template_name: string
  draft_text: string
  missing_fields: string[]
  missing_materials: string[]
  cited_laws: string[]
  next_steps: string[]
}
```

```json
{
  "template_type": "complaint_letter",
  "template_name": "投诉信（商品质量纠纷）",
  "draft_text": "",
  "missing_fields": ["merchant_name"],
  "missing_materials": ["订单页面", "支付记录"],
  "cited_laws": [],
  "next_steps": [
    "请先补全必填字段后再重新生成或核对文书。",
    "优先补齐以下材料：订单页面、支付记录。",
    "先向商家或平台提交投诉信并保留提交记录。"
  ]
}
```

- [ ] **Step 2: Run the backend test suite to verify no regression**

Run: `PYTHONPATH=. python -m pytest tests/unit tests/integration -q`  
Expected: PASS with all existing and new tests green.

- [ ] **Step 3: Run real API end-to-end checks with live model access**

Run: `PYTHONPATH=. python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`

Then issue real requests against:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/draft -ContentType "application/json" -Body '{"template_type":"complaint_letter","facts":{"consumer_name":"张三","consumer_contact":"13800000000","merchant_name":"某商家","merchant_contact_or_address":"北京市朝阳区某路1号","platform_name":"某平台","product_name":"蓝牙耳机","order_no":"ORDER-001","purchase_channel":"网购","purchase_time":"2026-04-20","payment_amount":"399","issue_summary":"商品存在明显杂音","issue_details":"收到商品后发现左右声道杂音，已拍照录像。","negotiation_history":"已与商家客服和平台客服沟通，并保留聊天记录。","claim_items":"要求退货退款并承担运费","claim_deadline_days":"7","attachments_summary":"订单页面、支付记录、聊天记录、商品问题照片、平台处理记录","complaint_date":"2026-05-04"}}'
```

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/draft -ContentType "application/json" -Body '{"template_type":"demand_letter","facts":{"sender_name":"张三","sender_contact":"13800000000","receiver_name":"某商家","receiver_address_or_contact":"杭州市某区某路1号","platform_name":"某电商平台","product_name":"扫地机器人","order_no":"ORDER-002","transaction_time":"2026-04-18","payment_amount":"1699","issue_summary":"商品存在严重质量问题","breach_summary":"商家拒绝退货退款","negotiation_history":"已与商家及平台多次协商并保留聊天记录","demand_items":"退还货款并承担退货运费","deadline_days":"7","letter_date":"2026-05-04","attachments_summary":"订单页面、支付截图、聊天记录、商品问题视频、平台处理记录"}}'
```

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/draft -ContentType "application/json" -Body '{"template_type":"lawsuit_draft","facts":{"court_name":"杭州市西湖区人民法院","plaintiff_name":"张三","plaintiff_gender":"男","plaintiff_birth_date":"1992-03-04","plaintiff_ethnicity":"汉","plaintiff_address":"浙江省杭州市西湖区某路8号","plaintiff_contact":"13800000000","defendant_name":"某电子商务有限公司","defendant_type":"公司","defendant_address":"浙江省杭州市某区某园区","cause_of_action":"网络购物合同纠纷","claims":"1. 判令被告退还货款1699元；2. 判令被告承担本案诉讼费用。","facts_and_reasons":"原告在被告店铺购买扫地机器人，商品存在严重质量问题，被告拒绝退款。","evidence_list":"订单页面、支付记录、聊天记录、商品问题照片、平台处理记录、营业执照截图","filing_date":"2026-05-04"}}'
```

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/draft -ContentType "application/json" -Body '{"template_type":"complaint_letter","facts":{"consumer_name":"张三"}}'
```

Expected:

- complete complaint case returns non-empty `draft_text`
- complete demand case returns non-empty `draft_text`
- complete lawsuit case returns non-empty `draft_text`
- incomplete case returns empty `draft_text`
- every case returns `missing_materials` as an array
- `next_steps` varies by `template_type` and missing state

- [ ] **Step 4: If a real-case failure appears, debug the root cause before closing**

Run failing test or request again after the fix:

```bash
PYTHONPATH=. python -m pytest tests/unit tests/integration -q
```

Expected: PASS after the root-cause fix, not a case-specific patch.

- [ ] **Step 5: Commit docs or verification-driven fixes**

```bash
git add docs/frontend_api_contract.md
git commit -m "docs: update draft guidance frontend contract"
```

## Self-Review

- Spec coverage:
  - deterministic `next_steps`: Task 1 + Task 2
  - `missing_materials`: Task 1 + Task 2
  - frontend contract update: Task 3
  - real integration verification: Task 3
- Placeholder scan:
  - no `TBD`, `TODO`, or undefined code steps remain
- Type consistency:
  - `missing_materials` is consistently `list[str]`
  - guidance entrypoint stays `build_draft_guidance(template_type, facts, missing_fields)`

Plan complete and saved to `docs/superpowers/plans/2026-05-04-draft-guidance.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints
