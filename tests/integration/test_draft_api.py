from fastapi.testclient import TestClient

from app.dependencies import get_draft_service, get_template_service
from app.main import create_app
from app.schemas.draft import DraftResponse, DraftTemplate
from app.services.exceptions import UpstreamModelError


class FakeDraftServiceWithMissingFields:
    def generate(self, request):
        return DraftResponse(
            template_type=request.template_type,
            template_name="投诉信（商品质量纠纷）",
            draft_text="",
            missing_fields=["merchant_name"],
            cited_laws=[],
            next_steps=["补全必填字段后重新生成文书草稿。"],
        )


class FakeDraftServiceWithRenderedText:
    def generate(self, request):
        return DraftResponse(
            template_type=request.template_type,
            template_name="投诉信（商品质量纠纷）",
            draft_text="投诉信正文",
            missing_fields=[],
            cited_laws=["《中华人民共和国消费者权益保护法》第二十四条"],
            next_steps=["核对后提交。"],
        )


class FakeFailingDraftService:
    def generate(self, request):
        raise UpstreamModelError()


class FakeTemplateService:
    def __init__(self) -> None:
        self._templates = {
            "complaint_letter": DraftTemplate.model_validate(
                {
                    "template_id": "tpl-complaint",
                    "template_name": "投诉信（商品质量纠纷）",
                    "doc_type": "complaint",
                    "template_type": "complaint_letter",
                    "scene": "商品质量纠纷",
                    "status": "active",
                    "required_fields": [
                        {"name": "consumer_name", "label": "投诉人姓名", "type": "string"}
                    ],
                    "optional_fields": [
                        {"name": "consumer_id_no", "label": "投诉人证件号", "type": "string"}
                    ],
                    "derived_placeholders": [],
                    "suggested_citations": [],
                    "template_text": "正文",
                }
            ),
            "demand_letter": DraftTemplate.model_validate(
                {
                    "template_id": "tpl-demand",
                    "template_name": "催告函（退款退货）",
                    "doc_type": "letter",
                    "template_type": "demand_letter",
                    "scene": "退款退货",
                    "status": "active",
                    "required_fields": [
                        {"name": "sender_name", "label": "发函人姓名", "type": "string"}
                    ],
                    "optional_fields": [],
                    "derived_placeholders": [],
                    "suggested_citations": [],
                    "template_text": "正文",
                }
            ),
        }

    def list_templates(self):
        return [self._templates["complaint_letter"], self._templates["demand_letter"]]

    def get_template(self, template_type: str):
        try:
            return self._templates[template_type]
        except KeyError as exc:
            raise KeyError(f"unknown template_type: {template_type}") from exc


def test_post_draft_returns_missing_fields_when_facts_incomplete():
    app = create_app()
    app.dependency_overrides[get_draft_service] = lambda: FakeDraftServiceWithMissingFields()
    client = TestClient(app)

    response = client.post(
        "/draft",
        json={
            "template_type": "complaint_letter",
            "facts": {"consumer_name": "张三"},
        },
    )

    assert response.status_code == 200
    assert response.json()["missing_fields"] == ["merchant_name"]


def test_post_draft_returns_rendered_text_when_complete():
    app = create_app()
    app.dependency_overrides[get_draft_service] = lambda: FakeDraftServiceWithRenderedText()
    client = TestClient(app)

    response = client.post(
        "/draft",
        json={
            "template_type": "complaint_letter",
            "facts": {"consumer_name": "张三", "merchant_name": "某商家"},
        },
    )

    assert response.status_code == 200
    assert response.json()["draft_text"] == "投诉信正文"


def test_post_draft_response_shape_is_stable():
    app = create_app()
    app.dependency_overrides[get_draft_service] = lambda: FakeDraftServiceWithMissingFields()
    client = TestClient(app)

    response = client.post(
        "/draft",
        json={
            "template_type": "complaint_letter",
            "facts": {"consumer_name": "张三"},
        },
    )

    body = response.json()
    assert sorted(body.keys()) == [
        "cited_laws",
        "draft_text",
        "missing_fields",
        "next_steps",
        "template_name",
        "template_type",
    ]


def test_post_draft_returns_502_when_upstream_model_call_fails():
    app = create_app()
    app.dependency_overrides[get_draft_service] = lambda: FakeFailingDraftService()
    client = TestClient(app)

    response = client.post(
        "/draft",
        json={
            "template_type": "complaint_letter",
            "facts": {"consumer_name": "张三"},
        },
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "上游模型调用失败"}


def test_get_draft_templates_returns_template_list():
    app = create_app()
    app.dependency_overrides[get_template_service] = lambda: FakeTemplateService()
    client = TestClient(app)

    response = client.get("/draft/templates")

    assert response.status_code == 200
    assert response.json() == {
        "templates": [
            {
                "template_type": "complaint_letter",
                "template_name": "投诉信（商品质量纠纷）",
                "required_fields": [
                    {"name": "consumer_name", "label": "投诉人姓名", "type": "string"}
                ],
                "optional_fields": [
                    {"name": "consumer_id_no", "label": "投诉人证件号", "type": "string"}
                ],
            },
            {
                "template_type": "demand_letter",
                "template_name": "催告函（退款退货）",
                "required_fields": [
                    {"name": "sender_name", "label": "发函人姓名", "type": "string"}
                ],
                "optional_fields": [],
            },
        ]
    }


def test_get_draft_templates_response_shape_is_stable():
    app = create_app()
    app.dependency_overrides[get_template_service] = lambda: FakeTemplateService()
    client = TestClient(app)

    response = client.get("/draft/templates")

    body = response.json()
    assert sorted(body.keys()) == ["templates"]
    assert sorted(body["templates"][0].keys()) == [
        "optional_fields",
        "required_fields",
        "template_name",
        "template_type",
    ]


def test_get_draft_template_by_type_returns_single_template():
    app = create_app()
    app.dependency_overrides[get_template_service] = lambda: FakeTemplateService()
    client = TestClient(app)

    response = client.get("/draft/templates/complaint_letter")

    assert response.status_code == 200
    assert response.json() == {
        "template_type": "complaint_letter",
        "template_name": "投诉信（商品质量纠纷）",
        "required_fields": [
            {"name": "consumer_name", "label": "投诉人姓名", "type": "string"}
        ],
        "optional_fields": [
            {"name": "consumer_id_no", "label": "投诉人证件号", "type": "string"}
        ],
    }


def test_get_draft_template_by_type_returns_404_for_unknown_template():
    app = create_app()
    app.dependency_overrides[get_template_service] = lambda: FakeTemplateService()
    client = TestClient(app)

    response = client.get("/draft/templates/not_exists")

    assert response.status_code == 404
    assert response.json() == {"detail": "unknown template_type: not_exists"}


def test_get_template_service_returns_shared_instance():
    first = get_template_service()
    second = get_template_service()

    assert first is second
