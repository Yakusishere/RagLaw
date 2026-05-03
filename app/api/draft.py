from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_draft_service
from app.schemas.draft import DraftRequest, DraftResponse
from app.services.exceptions import UpstreamModelError

router = APIRouter()


@router.post("/draft", response_model=DraftResponse)
def draft(
    payload: DraftRequest,
    draft_service=Depends(get_draft_service),
) -> DraftResponse:
    try:
        return draft_service.generate(payload)
    except UpstreamModelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
