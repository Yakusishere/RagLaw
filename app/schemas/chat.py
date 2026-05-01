from pydantic import BaseModel

from app.schemas.retrieval import CitationPayload


class ChatRequest(BaseModel):
    query: str


class ChatAnswer(BaseModel):
    summary: str
    basis: list[str]
    suggested_steps: list[str]
    risk_notes: list[str]
    insufficient_basis: bool


class ChatResponse(BaseModel):
    query: str
    answer: ChatAnswer
    citations: list[CitationPayload]
    retrieval: dict[str, int]
