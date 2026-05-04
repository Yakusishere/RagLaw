from fastapi import APIRouter, Depends, HTTPException

from app.dependencies import get_retrieval_service
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.exceptions import UpstreamDependencyError
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(
    payload: RetrievalRequest,
    service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponse:
    try:
        return service.retrieve(payload.query, payload.top_k)
    except UpstreamDependencyError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
