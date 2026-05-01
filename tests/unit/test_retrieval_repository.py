from app.db.repositories.retrieval_repository import (
    build_keyword_terms,
    build_keyword_search_sql,
    build_vector_search_sql,
)


def test_vector_sql_limits_to_enabled_law_and_rule_chunks():
    sql = build_vector_search_sql()
    assert "rag.chunk_embeddings" in sql
    assert "enabled_for_retrieval = true" in sql
    assert "c.doc_type IN ('law', 'rule')" in sql
    assert "ORDER BY vector_score DESC" in sql


def test_keyword_sql_uses_search_text_and_top_k_limit():
    sql = build_keyword_search_sql()
    assert "unnest(%(keyword_terms)s::text[])" in sql
    assert "%(keyword_weight_total)s" in sql
    assert "keyword_score > 0" in sql
    assert "LIMIT %(top_k)s" in sql


def test_build_keyword_terms_extracts_meaningful_terms_from_chinese_question():
    terms = build_keyword_terms("商家拒绝退款怎么办")

    assert "拒绝" in terms
    assert "退款" in terms
    assert "拒绝退款" in terms
    assert "怎么办" not in terms


def test_build_keyword_terms_removes_question_fillers_but_keeps_core_legal_phrase():
    terms = build_keyword_terms("平台内商家虚假宣传如何维权")

    assert "虚假宣传" in terms
    assert "维权" in terms
    assert "如何" not in terms


def test_build_keyword_terms_keeps_late_phrases_in_long_questions():
    terms = build_keyword_terms("电商平台知道商家侵害消费者权益还要承担责任吗")

    assert "侵害消费者权益" in terms
    assert "承担责任" in terms
