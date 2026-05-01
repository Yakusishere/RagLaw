from app.schemas.retrieval import RetrievalCandidate
from app.services.citation_service import build_citation


def test_build_citation_preserves_empty_source_url():
    candidate = RetrievalCandidate(
        chunk_id="doc:article:0001",
        doc_type="law",
        title="中华人民共和国消费者权益保护法",
        article_no="第二十四条",
        chunk_text="第二十四条 经营者提供的商品或者服务不符合质量要求的...",
        citation_label="《中华人民共和国消费者权益保护法》第二十四条",
        source_name="用户提供资料",
        source_url="",
        effective_date="2013-10-25",
        vector_score=0.9,
        keyword_score=0.5,
        hybrid_score=0.8,
    )
    citation = build_citation(candidate)
    assert citation.citation_label == "《中华人民共和国消费者权益保护法》第二十四条"
    assert citation.source_url == ""
