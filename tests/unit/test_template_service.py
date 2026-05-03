from app.services.template_service import FileTemplateService


def test_template_service_loads_complaint_template_from_phase2_materials():
    service = FileTemplateService()

    template = service.get_template("complaint_letter")

    assert template.template_type == "complaint_letter"
    assert template.template_name == "投诉信（商品质量纠纷）"
    assert "consumer_name" in [field["name"] for field in template.required_fields]


def test_template_service_reports_unknown_template_type():
    service = FileTemplateService()

    try:
        service.get_template("not_exists")
    except KeyError as exc:
        assert "not_exists" in str(exc)
    else:
        raise AssertionError("expected KeyError")
