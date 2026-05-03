from fastapi import APIRouter, Depends

from app.dependencies import get_draft_service
from app.schemas.draft import DraftRequest, DraftResponse

router = APIRouter()


@router.post("/draft", response_model=DraftResponse)
def draft(
    payload: DraftRequest,
    draft_service=Depends(get_draft_service),
) -> DraftResponse:
    return draft_service.generate(payload)
