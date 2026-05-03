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
