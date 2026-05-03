import json

from pydantic import ValidationError

from app.services.template_service import FileTemplateService


def _template_payload(template_type: str = "complaint_letter") -> dict:
    return {
        "template_id": f"{template_type}_v1",
        "template_name": "投诉信（商品质量纠纷）",
        "doc_type": "template",
        "template_type": template_type,
        "scene": "quality_dispute",
        "status": "draft_ready",
        "required_fields": [
            {"name": "consumer_name", "label": "投诉人姓名", "type": "string"}
        ],
        "optional_fields": [],
        "derived_placeholders": [],
        "suggested_citations": [],
        "template_text": "投诉信正文",
    }


def _write_template_file(template_dir, filename: str, payload: dict) -> None:
    template_dir.mkdir(parents=True, exist_ok=True)
    (template_dir / filename).write_text(
        json.dumps(payload, ensure_ascii=False),
        encoding="utf-8",
    )


def test_template_service_loads_template_from_given_directory(tmp_path):
    _write_template_file(
        tmp_path,
        "template_complaint.json",
        _template_payload(),
    )
    service = FileTemplateService(template_dir=tmp_path)

    template = service.get_template("complaint_letter")

    assert template.template_type == "complaint_letter"
    assert template.template_name == "投诉信（商品质量纠纷）"
    assert "consumer_name" in [field.name for field in template.required_fields]


def test_template_service_reports_unknown_template_type(tmp_path):
    _write_template_file(
        tmp_path,
        "template_complaint.json",
        _template_payload(),
    )
    service = FileTemplateService(template_dir=tmp_path)

    try:
        service.get_template("not_exists")
    except KeyError as exc:
        assert "not_exists" in str(exc)
    else:
        raise AssertionError("expected KeyError")


def test_template_service_rejects_duplicate_template_type(tmp_path):
    _write_template_file(
        tmp_path,
        "template_complaint_a.json",
        _template_payload("complaint_letter"),
    )
    _write_template_file(
        tmp_path,
        "template_complaint_b.json",
        _template_payload("complaint_letter"),
    )

    try:
        FileTemplateService(template_dir=tmp_path)
    except ValueError as exc:
        assert "complaint_letter" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_template_service_rejects_malformed_payload(tmp_path):
    payload = _template_payload()
    del payload["template_name"]
    _write_template_file(
        tmp_path,
        "template_complaint.json",
        payload,
    )

    try:
        FileTemplateService(template_dir=tmp_path)
    except ValidationError as exc:
        assert "template_name" in str(exc)
    else:
        raise AssertionError("expected ValidationError")
