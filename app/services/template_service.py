import json
from pathlib import Path

from app.schemas.draft import DraftTemplate, DraftTemplateType


TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "docs" / "phase2_materials"


class FileTemplateService:
    def __init__(self, template_dir: Path | None = None) -> None:
        self._template_dir = template_dir or TEMPLATES_DIR
        self._templates = self._load_templates()

    def get_template(self, template_type: str) -> DraftTemplate:
        try:
            return self._templates[template_type]
        except KeyError as exc:
            raise KeyError(f"unknown template_type: {template_type}") from exc

    def list_templates(self) -> list[DraftTemplate]:
        return [self._templates[template_type] for template_type in sorted(self._templates)]

    def _load_templates(self) -> dict[DraftTemplateType, DraftTemplate]:
        templates: dict[DraftTemplateType, DraftTemplate] = {}
        for template_path in self._template_dir.glob("template_*.json"):
            payload = json.loads(template_path.read_text(encoding="utf-8"))
            template = DraftTemplate.model_validate(payload)
            if template.template_type in templates:
                raise ValueError(f"duplicate template_type: {template.template_type}")
            templates[template.template_type] = template
        return templates
