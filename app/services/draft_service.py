import re

from app.schemas.draft import (
    DraftRequest,
    DraftResponse,
    DraftTemplate,
    DraftTemplateDerivedPlaceholder,
    DraftTemplateField,
)
from app.services.draft_guidance import build_draft_guidance

PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_]+)\s*}}")


def build_missing_fields(
    required_fields: list[DraftTemplateField],
    facts: dict[str, str],
) -> list[str]:
    missing_fields: list[str] = []
    for field in required_fields:
        value = facts.get(field.name, "").strip()
        if not value:
            missing_fields.append(field.name)
    return missing_fields


def build_retrieval_query(template_name: str, facts: dict[str, str]) -> str:
    fact_values = [value.strip() for value in facts.values() if value.strip()]
    return " ".join([template_name, *fact_values]).strip()


def build_template_field_map(template: DraftTemplate) -> dict[str, DraftTemplateField]:
    required_fields = list(getattr(template, "required_fields", []))
    optional_fields = list(getattr(template, "optional_fields", []))
    return {field.name: field for field in [*required_fields, *optional_fields]}


def extract_rule_prefix(rule: str) -> str | None:
    match = re.search(r"“([^”]*?)\.\.\.”", rule)
    if match:
        return match.group(1)
    match = re.search(r"“([^”]+)”", rule)
    if match:
        return match.group(1).replace("...", "")
    return None


def render_derived_placeholder(
    placeholder: DraftTemplateDerivedPlaceholder,
    facts: dict[str, str],
    field_map: dict[str, DraftTemplateField],
) -> str:
    values = [facts.get(name, "").strip() for name in placeholder.from_]
    primary_value = next((value for value in values if value), "")

    if placeholder.name == "attachments_count_or_default":
        return primary_value or "按被告人数提交"
    if placeholder.name == "legal_basis_or_default":
        return primary_value
    if not primary_value:
        return ""

    rule_prefix = extract_rule_prefix(placeholder.rule)
    if rule_prefix is not None:
        return f"{rule_prefix}{primary_value}"

    source_field = field_map.get(placeholder.from_[0])
    label = source_field.label if source_field else placeholder.from_[0]
    return f"{label}：{primary_value}"


def render_template_text(template: DraftTemplate, facts: dict[str, str]) -> str:
    field_map = build_template_field_map(template)
    replacements = {name: value.strip() for name, value in facts.items()}

    for placeholder in getattr(template, "derived_placeholders", []):
        replacements[placeholder.name] = render_derived_placeholder(
            placeholder,
            facts,
            field_map,
        )

    rendered = PLACEHOLDER_PATTERN.sub(
        lambda match: replacements.get(match.group(1), ""),
        template.template_text,
    )
    rendered = "\n".join(line.rstrip() for line in rendered.splitlines())
    return re.sub(r"\n{3,}", "\n\n", rendered).strip()


class DraftService:
    def __init__(self, template_service, retrieval_service, llm_service) -> None:
        self._template_service = template_service
        self._retrieval_service = retrieval_service
        self._llm_service = llm_service

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

        retrieval_response = self._retrieval_service.retrieve(
            build_retrieval_query(template.template_name, request.facts)
        )
        rendered_template_text = render_template_text(template, request.facts)
        draft_text = self._llm_service.draft_document(
            template_text=rendered_template_text,
            facts=request.facts,
            retrieval_response=retrieval_response,
        )

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
