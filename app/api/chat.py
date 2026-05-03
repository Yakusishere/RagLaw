from collections.abc import Iterator
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse

from app.dependencies import get_chat_service, get_retrieval_service
from app.schemas.chat import ChatRequest, ChatResponse, ChatStreamEvent
from app.services.exceptions import UpstreamModelError
from app.services.llm_service import LLMService
from app.services.retrieval_service import RetrievalService

router = APIRouter()


def encode_sse_event(event: ChatStreamEvent) -> str:
    payload = json.dumps(
        jsonable_encoder(event.data),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return f"event: {event.event}\ndata: {payload}\n\n"


def encode_error_sse_event(message: str) -> str:
    return encode_sse_event(ChatStreamEvent(event="error", data={"message": message}))


def stream_chat_events(
    payload: ChatRequest,
    retrieval_service: RetrievalService,
    chat_service: LLMService,
) -> Iterator[str]:
    try:
        retrieval_response = retrieval_service.retrieve(payload.query)
        for event in chat_service.stream_answer(retrieval_response):
            yield encode_sse_event(event)
    except UpstreamModelError as exc:
        yield encode_error_sse_event(str(exc))
    except Exception as exc:
        message = str(exc) or "stream failed"
        yield encode_error_sse_event(message)


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    chat_service: LLMService = Depends(get_chat_service),
) -> ChatResponse:
    retrieval_response = retrieval_service.retrieve(payload.query)
    try:
        return chat_service.answer(retrieval_response)
    except UpstreamModelError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/chat/stream")
def chat_stream(
    payload: ChatRequest,
    retrieval_service: RetrievalService = Depends(get_retrieval_service),
    chat_service: LLMService = Depends(get_chat_service),
) -> StreamingResponse:
    return StreamingResponse(
        stream_chat_events(payload, retrieval_service, chat_service),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
