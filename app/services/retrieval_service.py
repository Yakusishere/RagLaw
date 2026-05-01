from app.schemas.retrieval import (
    RetrievalCandidate,
    RetrievalResponse,
    RetrievalResultItem,
)
from app.services.citation_service import build_citation
from app.services.query_normalization import normalize_query


def merge_ranked_candidates(
    vector_hits: list[RetrievalCandidate],
    keyword_hits: list[RetrievalCandidate],
    final_top_k: int,
) -> list[RetrievalCandidate]:
    merged: dict[str, RetrievalCandidate] = {}

    for candidate in vector_hits + keyword_hits:
        existing = merged.get(candidate.chunk_id)
        if existing is None:
            merged[candidate.chunk_id] = candidate.model_copy(deep=True)
            continue
        existing.vector_score = max(existing.vector_score or 0.0, candidate.vector_score or 0.0) or None
        existing.keyword_score = max(existing.keyword_score or 0.0, candidate.keyword_score or 0.0) or None

    for candidate in merged.values():
        doc_bonus = 0.05 if candidate.doc_type == "law" else 0.0
        candidate.hybrid_score = (
            (candidate.vector_score or 0.0) * 0.85
            + (candidate.keyword_score or 0.0) * 0.15
            + doc_bonus
        )

    ranked = sorted(
        merged.values(),
        key=lambda item: (item.hybrid_score, item.doc_type == "law"),
        reverse=True,
    )
    return ranked[:final_top_k]


class RetrievalService:
    def __init__(self, repository, embedding_client, settings):
        self._repository = repository
        self._embedding_client = embedding_client
        self._settings = settings

    def retrieve(self, query: str, top_k: int | None = None) -> RetrievalResponse:
        normalized = normalize_query(query)
        final_top_k = top_k or self._settings.retrieval_final_top_k
        vector_hits = self._repository.vector_search(
            query_embedding=self._embedding_client.embed_query(normalized),
            model_name=self._settings.openai_embedding_model,
            top_k=self._settings.retrieval_vector_top_k,
        )
        keyword_hits = self._repository.keyword_search(
            normalized_query=normalized,
            top_k=self._settings.retrieval_keyword_top_k,
        )
        merged = merge_ranked_candidates(vector_hits, keyword_hits, final_top_k)
        results = [
            RetrievalResultItem(
                chunk_id=item.chunk_id,
                doc_type=item.doc_type,
                title=item.title,
                article_no=item.article_no,
                chunk_text=item.chunk_text,
                citation=build_citation(item),
                scores={
                    "vector_score": item.vector_score,
                    "keyword_score": item.keyword_score,
                    "hybrid_score": item.hybrid_score,
                },
            )
            for item in merged
        ]
        return RetrievalResponse(query=normalized, results=results)
