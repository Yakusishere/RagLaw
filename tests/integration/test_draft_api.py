from fastapi.testclient import TestClient

from app.dependencies import get_draft_service
from app.main import create_app
from app.schemas.draft import DraftResponse


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
