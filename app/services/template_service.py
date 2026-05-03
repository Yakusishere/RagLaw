import json
from pathlib import Path
from types import SimpleNamespace


class FileTemplateService:
    def __init__(self) -> None:
        self._templates = self._load_templates()

    def get_template(self, template_type: str):
        try:
            return self._templates[template_type]
        except KeyError as exc:
            raise KeyError(f"unknown template_type: {template_type}") from exc

    def _load_templates(self) -> dict[str, SimpleNamespace]:
        templates: dict[str, SimpleNamespace] = {}
        for template_path in self._templates_dir().glob("template_*.json"):
            payload = json.loads(template_path.read_text(encoding="utf-8"))
            templates[payload["template_type"]] = SimpleNamespace(**payload)
        return templates

    def _templates_dir(self) -> Path:
        templates_dir = Path(__file__).resolve().parents[2] / "docs" / "phase2_materials"
        if templates_dir.is_dir():
            return templates_dir
        raise FileNotFoundError("docs/phase2_materials not found")
