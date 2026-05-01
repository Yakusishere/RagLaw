from app.db.repositories.retrieval_repository import (
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
    assert "c.search_text ILIKE" in sql
    assert "LIMIT %(top_k)s" in sql
