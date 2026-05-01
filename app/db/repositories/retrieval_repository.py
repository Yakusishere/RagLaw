import re

from psycopg import Connection

from app.schemas.retrieval import RetrievalCandidate

QUESTION_FILLERS = (
    "怎么办",
    "请问",
    "如何",
    "怎么",
    "是否",
    "还能",
    "还要",
    "可以",
    "吗",
    "么",
    "呢",
)
GENERIC_TERMS = {
    "商家",
    "平台",
    "商户",
    "卖家",
    "店家",
    "经营者",
    "消费者",
    "商品",
    "服务",
    "电商",
    "网购",
}
QUERY_SEGMENT_PATTERN = re.compile(r"[0-9A-Za-z\u4e00-\u9fff]+")
MAX_KEYWORD_NGRAM_SIZE = 7
MAX_KEYWORD_TERMS = 128


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
WITH query_terms AS (
    SELECT term
    FROM unnest(%(keyword_terms)s::text[]) AS term
),
scored_candidates AS (
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
    c.article_no_int,
    LEAST(
        1.0,
        CASE
            WHEN c.search_text ILIKE %(full_query_pattern)s THEN 0.2
            ELSE 0.0
        END
        + COALESCE(
            SUM(
                CASE
                    WHEN c.search_text ILIKE ('%%' || qt.term || '%%') THEN
                        CASE
                            WHEN char_length(qt.term) >= 6 THEN 5.0
                            WHEN char_length(qt.term) = 5 THEN 4.0
                            WHEN char_length(qt.term) = 4 THEN 3.0
                            WHEN char_length(qt.term) = 3 THEN 2.0
                            ELSE 1.0
                        END
                    ELSE 0.0
                END
            ),
            0.0
        ) / NULLIF(%(keyword_weight_total)s, 0.0)
    ) AS keyword_score
FROM rag.chunks c
CROSS JOIN query_terms qt
WHERE c.enabled_for_retrieval = true
  AND c.doc_type IN ('law', 'rule')
GROUP BY
    c.chunk_id,
    c.doc_type,
    c.title,
    c.article_no,
    c.chunk_text,
    c.citation_label,
    c.source_name,
    c.source_url,
    c.effective_date,
    c.article_no_int
)
SELECT
    chunk_id,
    doc_type,
    title,
    article_no,
    chunk_text,
    citation_label,
    source_name,
    source_url,
    effective_date,
    keyword_score
FROM scored_candidates
WHERE keyword_score > 0
ORDER BY keyword_score DESC, doc_type ASC, article_no_int NULLS LAST
LIMIT %(top_k)s
""".strip()


def build_keyword_terms(normalized_query: str) -> list[str]:
    cleaned = normalized_query.strip()
    for filler in QUESTION_FILLERS:
        cleaned = cleaned.replace(filler, " ")

    terms: list[str] = []
    seen: set[str] = set()
    for segment in QUERY_SEGMENT_PATTERN.findall(cleaned):
        compact_segment = segment.strip()
        if len(compact_segment) < 2:
            continue

        candidates: list[str] = []
        for size in range(min(MAX_KEYWORD_NGRAM_SIZE, len(compact_segment)), 1, -1):
            for start in range(len(compact_segment) - size + 1):
                candidates.append(compact_segment[start : start + size])

        for candidate in candidates:
            if len(candidate) < 2:
                continue
            if candidate in QUESTION_FILLERS or candidate in GENERIC_TERMS:
                continue
            if candidate in seen:
                continue
            seen.add(candidate)
            terms.append(candidate)
            if len(terms) >= MAX_KEYWORD_TERMS:
                return terms

    return terms


def _keyword_term_weight(term: str) -> float:
    term_length = len(term)
    if term_length >= 6:
        return 5.0
    if term_length == 5:
        return 4.0
    if term_length == 4:
        return 3.0
    if term_length == 3:
        return 2.0
    return 1.0


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
        keyword_terms = build_keyword_terms(normalized_query)
        if not keyword_terms:
            return []

        with self._conn.cursor() as cur:
            cur.execute(
                build_keyword_search_sql(),
                {
                    "full_query_pattern": f"%{normalized_query}%",
                    "keyword_terms": keyword_terms,
                    "keyword_weight_total": sum(_keyword_term_weight(term) for term in keyword_terms),
                    "top_k": top_k,
                },
            )
            rows = cur.fetchall()
        return [RetrievalCandidate(**row, vector_score=None, hybrid_score=0.0) for row in rows]
