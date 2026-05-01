from app.schemas.retrieval import CitationPayload, RetrievalCandidate


def build_citation(candidate: RetrievalCandidate) -> CitationPayload:
    return CitationPayload(
        chunk_id=candidate.chunk_id,
        citation_label=candidate.citation_label,
        title=candidate.title,
        doc_type=candidate.doc_type,
        article_no=candidate.article_no,
        effective_date=candidate.effective_date,
        source_name=candidate.source_name,
        source_url=candidate.source_url or "",
    )
