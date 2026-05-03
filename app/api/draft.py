from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_draft_service, get_template_service
from app.schemas.draft import (
    DraftRequest,
    DraftResponse,
    DraftTemplate,
    DraftTemplateFieldResponse,
    DraftTemplateListResponse,
    DraftTemplateMetadataResponse,
)
from app.services.exceptions import UpstreamModelError

router = APIRouter()


def build_template_metadata_response(template: DraftTemplate) -> DraftTemplateMetadataResponse:
    return DraftTemplateMetadataResponse(
        template_type=template.template_type,
        template_name=template.template_name,
        required_fields=[
            DraftTemplateFieldResponse(
                name=field.name,
                label=field.label,
                type=field.type,
            )
            for field in template.required_fields
        ],
        optional_fields=[
            DraftTemplateFieldResponse(
                name=field.name,
                label=field.label,
                type=field.type,
            )
            for field in template.optional_fields
        ],
    )


@router.post("/draft", response_model=DraftResponse)
def draft(
    payload: DraftRequest,
    draft_service=Depends(get_draft_service),
) -> DraftResponse:
    try:
        return draft_service.generate(payload)
    except UpstreamModelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/draft/templates", response_model=DraftTemplateListResponse)
def list_draft_templates(
    template_service=Depends(get_template_service),
) -> DraftTemplateListResponse:
    return DraftTemplateListResponse(
        templates=[
            build_template_metadata_response(template)
            for template in template_service.list_templates()
        ]
    )


@router.get("/draft/templates/{template_type}", response_model=DraftTemplateMetadataResponse)
def get_draft_template(
    template_type: str,
    template_service=Depends(get_template_service),
) -> DraftTemplateMetadataResponse:
    try:
        template = template_service.get_template(template_type)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return build_template_metadata_response(template)
