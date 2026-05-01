from fastapi import APIRouter, Depends

from app.dependencies import get_chat_service, get_retrieval_service
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    chat_service: LLMService = Depends(get_chat_service),
) -> ChatResponse:
    retrieval_response = retrieval_service.retrieve(payload.query)
    return chat_service.answer(retrieval_response)
