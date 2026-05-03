from app.schemas.draft import DraftRequest, DraftResponse, DraftTemplateField


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


class DraftService:
    def __init__(self, template_service, retrieval_service, llm_service) -> None:
        self._template_service = template_service
        self._retrieval_service = retrieval_service
        self._llm_service = llm_service

    def generate(self, request: DraftRequest) -> DraftResponse:
        template = self._template_service.get_template(request.template_type)
        missing_fields = build_missing_fields(template.required_fields, request.facts)

        if missing_fields:
            return DraftResponse(
                template_type=request.template_type,
                template_name=template.template_name,
                draft_text="",
                missing_fields=missing_fields,
                cited_laws=[],
                next_steps=["补全必填字段后重新生成文书草稿。"],
            )

        retrieval_response = self._retrieval_service.retrieve(
            build_retrieval_query(template.template_name, request.facts)
        )
        draft_text = self._llm_service.draft_document(
            template_text=template.template_text,
            facts=request.facts,
            retrieval_response=retrieval_response,
        )

        return DraftResponse(
            template_type=request.template_type,
            template_name=template.template_name,
            draft_text=draft_text,
            missing_fields=[],
            cited_laws=[
                item.citation.citation_label for item in retrieval_response.results[:5]
            ],
            next_steps=["核对文书内容并补齐证据附件后再正式提交。"],
        )
