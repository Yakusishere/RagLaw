from psycopg import Connection

from app.schemas.retrieval import RetrievalCandidate


def build_vector_search_sql() -> str:
    return """
SELECT
    c.chunk_id,
    c.doc_type,
    c.title,
    c.article_no,
    c.chunk_text,
    c.citation_label,
    c.source_name,
    COALESCE(c.source_url, '') AS source_url,
    c.effective_date::text AS effective_date,
    1 - (ce.embedding <=> %(query_embedding)s::vector) AS vector_score
FROM rag.chunk_embeddings ce
JOIN rag.chunks c ON c.chunk_id = ce.chunk_id
WHERE c.enabled_for_retrieval = true
  AND c.doc_type IN ('law', 'rule')
  AND ce.model_name = %(model_name)s
ORDER BY vector_score DESC
LIMIT %(top_k)s
""".strip()


def build_keyword_search_sql() -> str:
    return """
SELECT
    c.chunk_id,
    c.doc_type,
    c.title,
    c.article_no,
    c.chunk_text,
    c.citation_label,
    c.source_name,
    COALESCE(c.source_url, '') AS source_url,
    c.effective_date::text AS effective_date,
    CASE
        WHEN c.search_text ILIKE %(exact_query)s THEN 1.0
        WHEN c.search_text ILIKE %(partial_query)s THEN 0.7
        ELSE 0.0
    END AS keyword_score
FROM rag.chunks c
WHERE c.enabled_for_retrieval = true
  AND c.doc_type IN ('law', 'rule')
  AND c.search_text ILIKE %(partial_query)s
ORDER BY keyword_score DESC, c.doc_type ASC, c.article_no_int NULLS LAST
LIMIT %(top_k)s
""".strip()


class RetrievalRepository:
    def __init__(self, conn: Connection):
        self._conn = conn

    def vector_search(
        self,
        *,
        query_embedding: list[float],
        model_name: str,
        top_k: int,
    ) -> list[RetrievalCandidate]:
        with self._conn.cursor() as cur:
            cur.execute(
                build_vector_search_sql(),
                {
                    "query_embedding": query_embedding,
                    "model_name": model_name,
                    "top_k": top_k,
                },
            )
            rows = cur.fetchall()
        return [RetrievalCandidate(**row, keyword_score=None, hybrid_score=0.0) for row in rows]

    def keyword_search(
        self,
        *,
        normalized_query: str,
        top_k: int,
    ) -> list[RetrievalCandidate]:
        with self._conn.cursor() as cur:
            cur.execute(
                build_keyword_search_sql(),
                {
                    "exact_query": normalized_query,
                    "partial_query": f"%{normalized_query}%",
                    "top_k": top_k,
                },
            )
            rows = cur.fetchall()
        return [RetrievalCandidate(**row, vector_score=None, hybrid_score=0.0) for row in rows]
