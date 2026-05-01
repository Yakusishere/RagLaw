from pydantic import BaseModel, Field


class CitationPayload(BaseModel):
    chunk_id: str
    citation_label: str
    title: str
    doc_type: str
    article_no: str | None = None
    effective_date: str | None = None
    source_name: str
    source_url: str = ""


class RetrievalCandidate(BaseModel):
    chunk_id: str
    doc_type: str
    title: str
    article_no: str | None = None
    chunk_text: str
    citation_label: str
    source_name: str
    source_url: str = ""
    effective_date: str | None = None
    vector_score: float | None = None
    keyword_score: float | None = None
    hybrid_score: float = Field(default=0.0)


class RetrievalRequest(BaseModel):
    query: str
    top_k: int | None = None


class RetrievalResultItem(BaseModel):
    chunk_id: str
    doc_type: str
    title: str
    article_no: str | None = None
    chunk_text: str
    citation: CitationPayload
    scores: dict[str, float | None]


class RetrievalResponse(BaseModel):
    query: str
    results: list[RetrievalResultItem]
