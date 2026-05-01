from fastapi import APIRouter, Depends

from app.dependencies import get_retrieval_service
from app.schemas.retrieval import RetrievalRequest, RetrievalResponse
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.post("/retrieve", response_model=RetrievalResponse)
def retrieve(
    payload: RetrievalRequest,
    service: RetrievalService = Depends(get_retrieval_service),
) -> RetrievalResponse:
    return service.retrieve(payload.query, payload.top_k)
