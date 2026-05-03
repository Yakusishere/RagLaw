import pytest

from app.services.template_service import FileTemplateService
from app.services import template_service


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


def test_template_service_does_not_fall_back_outside_worktree_docs(monkeypatch):
    local_templates_dir = (template_service.Path.cwd() / "docs" / "phase2_materials").resolve()
    outer_templates_dir = local_templates_dir.parents[3] / "docs" / "phase2_materials"

    original_is_dir = template_service.Path.is_dir

    def fake_is_dir(path):
        if path == local_templates_dir:
            return False
        if path == outer_templates_dir:
            return True
        return original_is_dir(path)

    monkeypatch.setattr(template_service.Path, "is_dir", fake_is_dir)

    service = FileTemplateService.__new__(FileTemplateService)

    with pytest.raises(FileNotFoundError):
        service._templates_dir()
