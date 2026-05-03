from typing import Literal

from pydantic import BaseModel, Field


DraftTemplateType = Literal[
    "complaint_letter",
    "demand_letter",
    "lawsuit_draft",
]


class DraftRequest(BaseModel):
    template_type: DraftTemplateType
    facts: dict[str, str] = Field(default_factory=dict)


class DraftResponse(BaseModel):
    template_type: DraftTemplateType
    template_name: str
    draft_text: str
    missing_fields: list[str]
    cited_laws: list[str]
    next_steps: list[str]


class DraftTemplateField(BaseModel):
    name: str
    label: str
    type: str


class DraftTemplateDerivedPlaceholder(BaseModel):
    name: str
    from_: list[str] = Field(alias="from")
    rule: str


class DraftTemplate(BaseModel):
    template_id: str
    template_name: str
    doc_type: str
    template_type: DraftTemplateType
    scene: str
    status: str
    required_fields: list[DraftTemplateField]
    optional_fields: list[DraftTemplateField] = Field(default_factory=list)
    derived_placeholders: list[DraftTemplateDerivedPlaceholder] = Field(default_factory=list)
    suggested_citations: list[str] = Field(default_factory=list)
    template_text: str
