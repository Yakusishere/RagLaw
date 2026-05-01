from app.schemas.retrieval import RetrievalCandidate
from app.services.retrieval_service import merge_ranked_candidates


def test_merge_ranked_candidates_deduplicates_by_chunk_id():
    vector_hits = [
        RetrievalCandidate(
            chunk_id="law:1",
            doc_type="law",
            title="法",
            article_no="第一条",
            chunk_text="a",
            citation_label="cite-a",
            source_name="src",
            source_url="",
            effective_date="2020-01-01",
            vector_score=0.9,
            keyword_score=None,
            hybrid_score=0.0,
        )
    ]
    keyword_hits = [
        RetrievalCandidate(
            chunk_id="law:1",
            doc_type="law",
            title="法",
            article_no="第一条",
            chunk_text="a",
            citation_label="cite-a",
            source_name="src",
            source_url="",
            effective_date="2020-01-01",
            vector_score=None,
            keyword_score=0.8,
            hybrid_score=0.0,
        )
    ]

    merged = merge_ranked_candidates(vector_hits, keyword_hits, final_top_k=8)

    assert len(merged) == 1
    assert merged[0].hybrid_score > 0.8


def test_merge_ranked_candidates_keeps_stronger_vector_match_ahead_of_keyword_boosted_hit():
    vector_hits = [
        RetrievalCandidate(
            chunk_id="law:vector-best",
            doc_type="law",
            title="法",
            article_no="第一条",
            chunk_text="a",
            citation_label="cite-a",
            source_name="src",
            source_url="",
            effective_date="2020-01-01",
            vector_score=0.694,
            keyword_score=None,
            hybrid_score=0.0,
        ),
        RetrievalCandidate(
            chunk_id="law:keyword-boosted",
            doc_type="law",
            title="法",
            article_no="第二条",
            chunk_text="b",
            citation_label="cite-b",
            source_name="src",
            source_url="",
            effective_date="2020-01-01",
            vector_score=0.639,
            keyword_score=None,
            hybrid_score=0.0,
        ),
    ]
    keyword_hits = [
        RetrievalCandidate(
            chunk_id="law:keyword-boosted",
            doc_type="law",
            title="法",
            article_no="第二条",
            chunk_text="b",
            citation_label="cite-b",
            source_name="src",
            source_url="",
            effective_date="2020-01-01",
            vector_score=None,
            keyword_score=0.245,
            hybrid_score=0.0,
        )
    ]

    merged = merge_ranked_candidates(vector_hits, keyword_hits, final_top_k=8)

    assert merged[0].chunk_id == "law:vector-best"
