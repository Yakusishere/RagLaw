CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.ingestion_runs (
    run_id uuid PRIMARY KEY,
    run_label text NOT NULL,
    manifest_path text NOT NULL,
    documents_path text NOT NULL,
    chunks_path text NOT NULL,
    source_stats jsonb NOT NULL DEFAULT '{}'::jsonb,
    status text NOT NULL CHECK (status IN ('loaded', 'promoted', 'superseded', 'failed')),
    loaded_at timestamptz NOT NULL DEFAULT now(),
    promoted_at timestamptz,
    notes text
);

CREATE TABLE IF NOT EXISTS rag.staging_documents (
    run_id uuid NOT NULL REFERENCES rag.ingestion_runs(run_id) ON DELETE CASCADE,
    document_id text NOT NULL,
    title text NOT NULL,
    canonical_title text NOT NULL,
    doc_type text NOT NULL CHECK (doc_type IN ('law', 'rule', 'case', 'template')),
    source_name text NOT NULL,
    source_url text,
    effective_date date,
    version_note text NOT NULL,
    file_path text NOT NULL,
    is_canonical boolean NOT NULL,
    enabled_for_retrieval boolean NOT NULL,
    subset_of text,
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    raw_text text NOT NULL,
    clean_text text NOT NULL,
    paragraph_count integer NOT NULL CHECK (paragraph_count >= 0),
    clean_line_count integer NOT NULL CHECK (clean_line_count >= 0),
    chunk_count integer NOT NULL CHECK (chunk_count >= 0),
    warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
    clean_text_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, document_id),
    UNIQUE (run_id, file_path),
    CONSTRAINT staging_documents_subset_fk
        FOREIGN KEY (run_id, subset_of)
        REFERENCES rag.staging_documents(run_id, document_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS rag.staging_chunks (
    run_id uuid NOT NULL REFERENCES rag.ingestion_runs(run_id) ON DELETE CASCADE,
    chunk_id text NOT NULL,
    document_id text NOT NULL,
    doc_type text NOT NULL CHECK (doc_type IN ('law', 'rule', 'case', 'template')),
    chunk_type text NOT NULL CHECK (
        chunk_type IN ('article', 'document', 'facts', 'issue', 'holding', 'template_block')
    ),
    chunk_order integer NOT NULL CHECK (chunk_order > 0),
    title text NOT NULL,
    canonical_title text NOT NULL,
    part_title text,
    chapter_title text,
    section_title text,
    article_no text,
    article_no_int integer CHECK (article_no_int IS NULL OR article_no_int > 0),
    chunk_text text NOT NULL,
    embedding_text_hash text,
    embedding_text text NOT NULL,
    search_text text NOT NULL,
    citation_label text NOT NULL,
    effective_date date,
    source_name text NOT NULL,
    source_url text,
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    is_canonical boolean NOT NULL,
    enabled_for_retrieval boolean NOT NULL,
    subset_of text,
    canonical_key text NOT NULL,
    chunk_text_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (run_id, chunk_id),
    CONSTRAINT staging_chunks_document_fk
        FOREIGN KEY (run_id, document_id)
        REFERENCES rag.staging_documents(run_id, document_id)
        ON DELETE CASCADE
        DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT staging_chunks_article_required
        CHECK (
            doc_type NOT IN ('law', 'rule')
            OR article_no IS NOT NULL
        )
);

ALTER TABLE rag.staging_chunks
    ADD COLUMN IF NOT EXISTS embedding_text_hash text;

CREATE UNIQUE INDEX IF NOT EXISTS staging_chunks_doc_order_uniq
    ON rag.staging_chunks (run_id, document_id, chunk_order);

CREATE UNIQUE INDEX IF NOT EXISTS staging_chunks_doc_article_uniq
    ON rag.staging_chunks (run_id, document_id, article_no)
    WHERE article_no IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS staging_chunks_enabled_canonical_uniq
    ON rag.staging_chunks (run_id, canonical_key)
    WHERE enabled_for_retrieval;

CREATE INDEX IF NOT EXISTS staging_chunks_lookup_idx
    ON rag.staging_chunks (run_id, document_id, enabled_for_retrieval, doc_type);

CREATE TABLE IF NOT EXISTS rag.documents (
    document_id text PRIMARY KEY,
    source_run_id uuid NOT NULL REFERENCES rag.ingestion_runs(run_id),
    title text NOT NULL,
    canonical_title text NOT NULL,
    doc_type text NOT NULL CHECK (doc_type IN ('law', 'rule', 'case', 'template')),
    source_name text NOT NULL,
    source_url text,
    effective_date date,
    version_note text NOT NULL,
    file_path text NOT NULL UNIQUE,
    is_canonical boolean NOT NULL,
    enabled_for_retrieval boolean NOT NULL,
    subset_of text,
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    raw_text text NOT NULL,
    clean_text text NOT NULL,
    paragraph_count integer NOT NULL CHECK (paragraph_count >= 0),
    clean_line_count integer NOT NULL CHECK (clean_line_count >= 0),
    chunk_count integer NOT NULL CHECK (chunk_count >= 0),
    warnings jsonb NOT NULL DEFAULT '[]'::jsonb,
    clean_text_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT documents_subset_fk
        FOREIGN KEY (subset_of)
        REFERENCES rag.documents(document_id)
        DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS rag.chunks (
    chunk_id text PRIMARY KEY,
    source_run_id uuid NOT NULL REFERENCES rag.ingestion_runs(run_id),
    document_id text NOT NULL REFERENCES rag.documents(document_id) ON DELETE CASCADE,
    doc_type text NOT NULL CHECK (doc_type IN ('law', 'rule', 'case', 'template')),
    chunk_type text NOT NULL CHECK (
        chunk_type IN ('article', 'document', 'facts', 'issue', 'holding', 'template_block')
    ),
    chunk_order integer NOT NULL CHECK (chunk_order > 0),
    title text NOT NULL,
    canonical_title text NOT NULL,
    part_title text,
    chapter_title text,
    section_title text,
    article_no text,
    article_no_int integer CHECK (article_no_int IS NULL OR article_no_int > 0),
    chunk_text text NOT NULL,
    embedding_text_hash text,
    embedding_text text NOT NULL,
    search_text text NOT NULL,
    citation_label text NOT NULL,
    effective_date date,
    source_name text NOT NULL,
    source_url text,
    tags jsonb NOT NULL DEFAULT '[]'::jsonb,
    is_canonical boolean NOT NULL,
    enabled_for_retrieval boolean NOT NULL,
    subset_of text,
    canonical_key text NOT NULL,
    chunk_text_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT chunks_article_required
        CHECK (
            doc_type NOT IN ('law', 'rule')
            OR article_no IS NOT NULL
        )
);

ALTER TABLE rag.chunks
    ADD COLUMN IF NOT EXISTS embedding_text_hash text;

CREATE UNIQUE INDEX IF NOT EXISTS chunks_doc_order_uniq
    ON rag.chunks (document_id, chunk_order);

CREATE UNIQUE INDEX IF NOT EXISTS chunks_doc_article_uniq
    ON rag.chunks (document_id, article_no)
    WHERE article_no IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS chunks_enabled_canonical_uniq
    ON rag.chunks (canonical_key)
    WHERE enabled_for_retrieval;

CREATE INDEX IF NOT EXISTS chunks_retrieval_filter_idx
    ON rag.chunks (enabled_for_retrieval, doc_type, document_id, article_no_int);

CREATE INDEX IF NOT EXISTS chunks_search_tsv_idx
    ON rag.chunks
    USING gin (to_tsvector('simple', search_text));

CREATE TABLE IF NOT EXISTS rag.embedding_runs (
    embedding_run_id uuid PRIMARY KEY,
    run_label text NOT NULL,
    source_ingestion_run_id uuid NOT NULL REFERENCES rag.ingestion_runs(run_id),
    embeddings_path text NOT NULL,
    model_name text NOT NULL,
    dimensions integer NOT NULL CHECK (dimensions > 0),
    distance_metric text NOT NULL CHECK (distance_metric IN ('cosine', 'l2', 'ip')),
    chunk_scope text NOT NULL CHECK (chunk_scope IN ('enabled_only', 'all_chunks')),
    expected_chunk_count integer NOT NULL CHECK (expected_chunk_count >= 0),
    status text NOT NULL CHECK (status IN ('loaded', 'promoted', 'superseded', 'failed')),
    loaded_at timestamptz NOT NULL DEFAULT now(),
    promoted_at timestamptz,
    notes text
);

CREATE TABLE IF NOT EXISTS rag.staging_chunk_embeddings (
    embedding_run_id uuid NOT NULL REFERENCES rag.embedding_runs(embedding_run_id) ON DELETE CASCADE,
    chunk_id text NOT NULL,
    embedding_text_hash text NOT NULL,
    embedding vector NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (embedding_run_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS staging_chunk_embeddings_lookup_idx
    ON rag.staging_chunk_embeddings (embedding_run_id, chunk_id);

CREATE TABLE IF NOT EXISTS rag.chunk_embeddings (
    chunk_id text NOT NULL REFERENCES rag.chunks(chunk_id) ON DELETE CASCADE,
    model_name text NOT NULL,
    embedding_run_id uuid NOT NULL REFERENCES rag.embedding_runs(embedding_run_id),
    source_ingestion_run_id uuid NOT NULL REFERENCES rag.ingestion_runs(run_id),
    distance_metric text NOT NULL CHECK (distance_metric IN ('cosine', 'l2', 'ip')),
    dimensions integer NOT NULL CHECK (dimensions > 0),
    embedding_text_hash text NOT NULL,
    embedding vector NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (chunk_id, model_name)
);

CREATE INDEX IF NOT EXISTS chunk_embeddings_model_idx
    ON rag.chunk_embeddings (model_name, source_ingestion_run_id);

CREATE INDEX IF NOT EXISTS chunk_embeddings_source_idx
    ON rag.chunk_embeddings (source_ingestion_run_id);

CREATE OR REPLACE FUNCTION rag.review_findings(p_run_id uuid)
RETURNS TABLE (
    severity text,
    check_name text,
    finding_count bigint,
    detail jsonb
)
LANGUAGE sql
AS $$
WITH selected_run AS (
    SELECT *
    FROM rag.ingestion_runs
    WHERE run_id = p_run_id
),
run_stats AS (
    SELECT
        (source_stats ->> 'document_count')::bigint AS expected_document_count,
        (source_stats ->> 'chunk_count')::bigint AS expected_chunk_count
    FROM selected_run
),
doc_stats AS (
    SELECT count(*)::bigint AS actual_document_count
    FROM rag.staging_documents
    WHERE run_id = p_run_id
),
chunk_stats AS (
    SELECT count(*)::bigint AS actual_chunk_count
    FROM rag.staging_chunks
    WHERE run_id = p_run_id
),
duplicate_enabled_keys AS (
    SELECT canonical_key, count(*) AS duplicate_count
    FROM rag.staging_chunks
    WHERE run_id = p_run_id
      AND enabled_for_retrieval
    GROUP BY canonical_key
    HAVING count(*) > 1
),
non_contiguous_documents AS (
    SELECT
        document_id,
        min(chunk_order) AS min_chunk_order,
        max(chunk_order) AS max_chunk_order,
        count(*) AS chunk_total
    FROM rag.staging_chunks
    WHERE run_id = p_run_id
    GROUP BY document_id
    HAVING min(chunk_order) <> 1
       OR max(chunk_order) <> count(*)
),
documents_with_warnings AS (
    SELECT document_id
    FROM rag.staging_documents
    WHERE run_id = p_run_id
      AND jsonb_array_length(warnings) > 0
),
documents_with_zero_chunks AS (
    SELECT d.document_id
    FROM rag.staging_documents d
    LEFT JOIN rag.staging_chunks c
      ON c.run_id = d.run_id
     AND c.document_id = d.document_id
    WHERE d.run_id = p_run_id
    GROUP BY d.document_id
    HAVING count(c.chunk_id) = 0
),
enabled_docs_missing_effective_date AS (
    SELECT document_id
    FROM rag.staging_documents
    WHERE run_id = p_run_id
      AND enabled_for_retrieval
      AND effective_date IS NULL
),
enabled_docs_missing_source_url AS (
    SELECT document_id
    FROM rag.staging_documents
    WHERE run_id = p_run_id
      AND enabled_for_retrieval
      AND coalesce(source_url, '') = ''
),
chunks_missing_article_no AS (
    SELECT chunk_id
    FROM rag.staging_chunks
    WHERE run_id = p_run_id
      AND doc_type IN ('law', 'rule')
      AND article_no IS NULL
),
chunks_missing_embedding_text_hash AS (
    SELECT chunk_id
    FROM rag.staging_chunks
    WHERE run_id = p_run_id
      AND coalesce(embedding_text_hash, '') = ''
),
doc_chunk_mismatch AS (
    SELECT d.document_id, d.chunk_count AS declared_chunk_count, count(c.chunk_id) AS actual_chunk_count
    FROM rag.staging_documents d
    LEFT JOIN rag.staging_chunks c
      ON c.run_id = d.run_id
     AND c.document_id = d.document_id
    WHERE d.run_id = p_run_id
    GROUP BY d.document_id, d.chunk_count
    HAVING d.chunk_count <> count(c.chunk_id)
)
SELECT *
FROM (
    SELECT
        'blocker'::text AS severity,
        'run_exists'::text AS check_name,
        CASE WHEN EXISTS (SELECT 1 FROM selected_run) THEN 0 ELSE 1 END::bigint AS finding_count,
        jsonb_build_object('run_id', p_run_id) AS detail
    UNION ALL
    SELECT
        'blocker',
        'document_count_match',
        CASE
            WHEN NOT EXISTS (SELECT 1 FROM selected_run) THEN 0
            WHEN (SELECT expected_document_count FROM run_stats) IS NULL THEN 0
            WHEN (SELECT expected_document_count FROM run_stats) = (SELECT actual_document_count FROM doc_stats) THEN 0
            ELSE 1
        END,
        jsonb_build_object(
            'expected', (SELECT expected_document_count FROM run_stats),
            'actual', (SELECT actual_document_count FROM doc_stats)
        )
    UNION ALL
    SELECT
        'blocker',
        'chunk_count_match',
        CASE
            WHEN NOT EXISTS (SELECT 1 FROM selected_run) THEN 0
            WHEN (SELECT expected_chunk_count FROM run_stats) IS NULL THEN 0
            WHEN (SELECT expected_chunk_count FROM run_stats) = (SELECT actual_chunk_count FROM chunk_stats) THEN 0
            ELSE 1
        END,
        jsonb_build_object(
            'expected', (SELECT expected_chunk_count FROM run_stats),
            'actual', (SELECT actual_chunk_count FROM chunk_stats)
        )
    UNION ALL
    SELECT
        'blocker',
        'duplicate_enabled_canonical_keys',
        count(*)::bigint,
        jsonb_build_object('sample_keys', coalesce(jsonb_agg(canonical_key) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT canonical_key, row_number() OVER (ORDER BY canonical_key) AS row_number
        FROM duplicate_enabled_keys
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'non_contiguous_chunk_order',
        count(*)::bigint,
        jsonb_build_object('sample_documents', coalesce(jsonb_agg(document_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT document_id, row_number() OVER (ORDER BY document_id) AS row_number
        FROM non_contiguous_documents
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'documents_with_zero_chunks',
        count(*)::bigint,
        jsonb_build_object('sample_documents', coalesce(jsonb_agg(document_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT document_id, row_number() OVER (ORDER BY document_id) AS row_number
        FROM documents_with_zero_chunks
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'document_declared_chunk_count_mismatch',
        count(*)::bigint,
        jsonb_build_object('sample_documents', coalesce(jsonb_agg(document_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT document_id, row_number() OVER (ORDER BY document_id) AS row_number
        FROM doc_chunk_mismatch
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'law_rule_chunks_missing_article_no',
        count(*)::bigint,
        jsonb_build_object('sample_chunks', coalesce(jsonb_agg(chunk_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT chunk_id, row_number() OVER (ORDER BY chunk_id) AS row_number
        FROM chunks_missing_article_no
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'chunks_missing_embedding_text_hash',
        count(*)::bigint,
        jsonb_build_object('sample_chunks', coalesce(jsonb_agg(chunk_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT chunk_id, row_number() OVER (ORDER BY chunk_id) AS row_number
        FROM chunks_missing_embedding_text_hash
    ) sampled
    UNION ALL
    SELECT
        'warning',
        'documents_with_parser_warnings',
        count(*)::bigint,
        jsonb_build_object('sample_documents', coalesce(jsonb_agg(document_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT document_id, row_number() OVER (ORDER BY document_id) AS row_number
        FROM documents_with_warnings
    ) sampled
    UNION ALL
    SELECT
        'warning',
        'enabled_documents_missing_effective_date',
        count(*)::bigint,
        jsonb_build_object('sample_documents', coalesce(jsonb_agg(document_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT document_id, row_number() OVER (ORDER BY document_id) AS row_number
        FROM enabled_docs_missing_effective_date
    ) sampled
    UNION ALL
    SELECT
        'warning',
        'enabled_documents_missing_source_url',
        count(*)::bigint,
        jsonb_build_object('sample_documents', coalesce(jsonb_agg(document_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT document_id, row_number() OVER (ORDER BY document_id) AS row_number
        FROM enabled_docs_missing_source_url
    ) sampled
) findings
ORDER BY
    CASE severity WHEN 'blocker' THEN 0 ELSE 1 END,
    check_name;
$$;

CREATE OR REPLACE FUNCTION rag.can_promote_run(p_run_id uuid)
RETURNS boolean
LANGUAGE sql
AS $$
SELECT NOT EXISTS (
    SELECT 1
    FROM rag.review_findings(p_run_id)
    WHERE severity = 'blocker'
      AND finding_count > 0
);
$$;

CREATE OR REPLACE FUNCTION rag.promote_run(p_run_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM rag.ingestion_runs
        WHERE run_id = p_run_id
    ) THEN
        RAISE EXCEPTION 'Ingestion run % does not exist.', p_run_id;
    END IF;

    IF NOT rag.can_promote_run(p_run_id) THEN
        RAISE EXCEPTION 'Ingestion run % failed blocker checks and cannot be promoted.', p_run_id;
    END IF;

    UPDATE rag.ingestion_runs
    SET status = 'superseded'
    WHERE status = 'promoted'
      AND run_id <> p_run_id;

    DELETE FROM rag.chunks;
    DELETE FROM rag.documents;

    INSERT INTO rag.documents (
        document_id,
        source_run_id,
        title,
        canonical_title,
        doc_type,
        source_name,
        source_url,
        effective_date,
        version_note,
        file_path,
        is_canonical,
        enabled_for_retrieval,
        subset_of,
        tags,
        raw_text,
        clean_text,
        paragraph_count,
        clean_line_count,
        chunk_count,
        warnings,
        clean_text_hash
    )
    SELECT
        document_id,
        run_id,
        title,
        canonical_title,
        doc_type,
        source_name,
        source_url,
        effective_date,
        version_note,
        file_path,
        is_canonical,
        enabled_for_retrieval,
        subset_of,
        tags,
        raw_text,
        clean_text,
        paragraph_count,
        clean_line_count,
        chunk_count,
        warnings,
        clean_text_hash
    FROM rag.staging_documents
    WHERE run_id = p_run_id
    ORDER BY document_id;

    INSERT INTO rag.chunks (
        chunk_id,
        source_run_id,
        document_id,
        doc_type,
        chunk_type,
        chunk_order,
        title,
        canonical_title,
        part_title,
        chapter_title,
        section_title,
        article_no,
        article_no_int,
        chunk_text,
        embedding_text,
        search_text,
        citation_label,
        effective_date,
        source_name,
        source_url,
        tags,
        is_canonical,
        enabled_for_retrieval,
        subset_of,
        canonical_key,
        chunk_text_hash
    )
    SELECT
        chunk_id,
        run_id,
        document_id,
        doc_type,
        chunk_type,
        chunk_order,
        title,
        canonical_title,
        part_title,
        chapter_title,
        section_title,
        article_no,
        article_no_int,
        chunk_text,
        embedding_text,
        search_text,
        citation_label,
        effective_date,
        source_name,
        source_url,
        tags,
        is_canonical,
        enabled_for_retrieval,
        subset_of,
        canonical_key,
        chunk_text_hash
    FROM rag.staging_chunks
    WHERE run_id = p_run_id
    ORDER BY document_id, chunk_order;

    UPDATE rag.ingestion_runs
    SET status = 'promoted',
        promoted_at = now()
    WHERE run_id = p_run_id;
END;
$$;

CREATE OR REPLACE FUNCTION rag.review_corpus()
RETURNS TABLE (
    severity text,
    check_name text,
    finding_count bigint,
    detail jsonb
)
LANGUAGE sql
AS $$
WITH promoted_run AS (
    SELECT *
    FROM rag.ingestion_runs
    WHERE status = 'promoted'
    ORDER BY promoted_at DESC NULLS LAST, loaded_at DESC
    LIMIT 1
),
run_stats AS (
    SELECT
        (source_stats ->> 'document_count')::bigint AS expected_document_count,
        (source_stats ->> 'chunk_count')::bigint AS expected_chunk_count
    FROM promoted_run
),
doc_stats AS (
    SELECT count(*)::bigint AS actual_document_count
    FROM rag.documents
),
chunk_stats AS (
    SELECT count(*)::bigint AS actual_chunk_count
    FROM rag.chunks
),
duplicate_enabled_keys AS (
    SELECT canonical_key
    FROM rag.chunks
    WHERE enabled_for_retrieval
    GROUP BY canonical_key
    HAVING count(*) > 1
),
enabled_docs_missing_effective_date AS (
    SELECT document_id
    FROM rag.documents
    WHERE enabled_for_retrieval
      AND effective_date IS NULL
),
enabled_docs_missing_source_url AS (
    SELECT document_id
    FROM rag.documents
    WHERE enabled_for_retrieval
      AND coalesce(source_url, '') = ''
),
chunks_missing_embedding_text_hash AS (
    SELECT chunk_id
    FROM rag.chunks
    WHERE coalesce(embedding_text_hash, '') = ''
)
SELECT *
FROM (
    SELECT
        'blocker'::text AS severity,
        'promoted_run_exists'::text AS check_name,
        CASE WHEN EXISTS (SELECT 1 FROM promoted_run) THEN 0 ELSE 1 END::bigint AS finding_count,
        jsonb_build_object('promoted_run_id', (SELECT run_id FROM promoted_run)) AS detail
    UNION ALL
    SELECT
        'blocker',
        'corpus_document_count_match',
        CASE
            WHEN NOT EXISTS (SELECT 1 FROM promoted_run) THEN 0
            WHEN (SELECT expected_document_count FROM run_stats) = (SELECT actual_document_count FROM doc_stats) THEN 0
            ELSE 1
        END,
        jsonb_build_object(
            'expected', (SELECT expected_document_count FROM run_stats),
            'actual', (SELECT actual_document_count FROM doc_stats)
        )
    UNION ALL
    SELECT
        'blocker',
        'corpus_chunk_count_match',
        CASE
            WHEN NOT EXISTS (SELECT 1 FROM promoted_run) THEN 0
            WHEN (SELECT expected_chunk_count FROM run_stats) = (SELECT actual_chunk_count FROM chunk_stats) THEN 0
            ELSE 1
        END,
        jsonb_build_object(
            'expected', (SELECT expected_chunk_count FROM run_stats),
            'actual', (SELECT actual_chunk_count FROM chunk_stats)
        )
    UNION ALL
    SELECT
        'blocker',
        'corpus_duplicate_enabled_canonical_keys',
        count(*)::bigint,
        jsonb_build_object('sample_keys', coalesce(jsonb_agg(canonical_key) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT canonical_key, row_number() OVER (ORDER BY canonical_key) AS row_number
        FROM duplicate_enabled_keys
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'corpus_chunks_missing_embedding_text_hash',
        count(*)::bigint,
        jsonb_build_object('sample_chunks', coalesce(jsonb_agg(chunk_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT chunk_id, row_number() OVER (ORDER BY chunk_id) AS row_number
        FROM chunks_missing_embedding_text_hash
    ) sampled
    UNION ALL
    SELECT
        'warning',
        'corpus_enabled_documents_missing_effective_date',
        count(*)::bigint,
        jsonb_build_object('sample_documents', coalesce(jsonb_agg(document_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT document_id, row_number() OVER (ORDER BY document_id) AS row_number
        FROM enabled_docs_missing_effective_date
    ) sampled
    UNION ALL
    SELECT
        'warning',
        'corpus_enabled_documents_missing_source_url',
        count(*)::bigint,
        jsonb_build_object('sample_documents', coalesce(jsonb_agg(document_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT document_id, row_number() OVER (ORDER BY document_id) AS row_number
        FROM enabled_docs_missing_source_url
    ) sampled
) findings
ORDER BY
    CASE severity WHEN 'blocker' THEN 0 ELSE 1 END,
    check_name;
$$;

CREATE OR REPLACE FUNCTION rag.review_embedding_run(p_embedding_run_id uuid)
RETURNS TABLE (
    severity text,
    check_name text,
    finding_count bigint,
    detail jsonb
)
LANGUAGE sql
AS $$
WITH selected_run AS (
    SELECT *
    FROM rag.embedding_runs
    WHERE embedding_run_id = p_embedding_run_id
),
current_corpus_run AS (
    SELECT run_id
    FROM rag.ingestion_runs
    WHERE status = 'promoted'
    ORDER BY promoted_at DESC NULLS LAST, loaded_at DESC
    LIMIT 1
),
expected_chunks AS (
    SELECT c.chunk_id, c.embedding_text_hash
    FROM rag.chunks c
    JOIN selected_run r
      ON c.source_run_id = r.source_ingestion_run_id
    WHERE
        (r.chunk_scope = 'all_chunks')
        OR (r.chunk_scope = 'enabled_only' AND c.enabled_for_retrieval)
),
expected_stats AS (
    SELECT count(*)::bigint AS expected_chunk_count
    FROM expected_chunks
),
actual_stats AS (
    SELECT count(*)::bigint AS actual_chunk_count
    FROM rag.staging_chunk_embeddings
    WHERE embedding_run_id = p_embedding_run_id
),
unknown_chunk_ids AS (
    SELECT s.chunk_id
    FROM rag.staging_chunk_embeddings s
    LEFT JOIN expected_chunks e
      ON e.chunk_id = s.chunk_id
    WHERE s.embedding_run_id = p_embedding_run_id
      AND e.chunk_id IS NULL
),
missing_chunk_ids AS (
    SELECT e.chunk_id
    FROM expected_chunks e
    LEFT JOIN rag.staging_chunk_embeddings s
      ON s.embedding_run_id = p_embedding_run_id
     AND s.chunk_id = e.chunk_id
    WHERE s.chunk_id IS NULL
),
dimension_mismatch AS (
    SELECT s.chunk_id
    FROM rag.staging_chunk_embeddings s
    CROSS JOIN selected_run r
    WHERE s.embedding_run_id = p_embedding_run_id
      AND vector_dims(s.embedding) <> r.dimensions
),
hash_mismatch AS (
    SELECT s.chunk_id
    FROM rag.staging_chunk_embeddings s
    JOIN expected_chunks e
      ON e.chunk_id = s.chunk_id
    WHERE s.embedding_run_id = p_embedding_run_id
      AND s.embedding_text_hash <> e.embedding_text_hash
)
SELECT *
FROM (
    SELECT
        'blocker'::text AS severity,
        'embedding_run_exists'::text AS check_name,
        CASE WHEN EXISTS (SELECT 1 FROM selected_run) THEN 0 ELSE 1 END::bigint AS finding_count,
        jsonb_build_object('embedding_run_id', p_embedding_run_id) AS detail
    UNION ALL
    SELECT
        'blocker',
        'embedding_source_run_is_current_corpus',
        CASE
            WHEN NOT EXISTS (SELECT 1 FROM selected_run) THEN 0
            WHEN (SELECT source_ingestion_run_id FROM selected_run) = (SELECT run_id FROM current_corpus_run) THEN 0
            ELSE 1
        END,
        jsonb_build_object(
            'source_ingestion_run_id', (SELECT source_ingestion_run_id FROM selected_run),
            'current_corpus_run_id', (SELECT run_id FROM current_corpus_run)
        )
    UNION ALL
    SELECT
        'blocker',
        'embedding_expected_chunk_count_match',
        CASE
            WHEN NOT EXISTS (SELECT 1 FROM selected_run) THEN 0
            WHEN (SELECT expected_chunk_count FROM expected_stats) = (SELECT expected_chunk_count FROM selected_run) THEN 0
            ELSE 1
        END,
        jsonb_build_object(
            'declared', (SELECT expected_chunk_count FROM selected_run),
            'actual_scope_count', (SELECT expected_chunk_count FROM expected_stats)
        )
    UNION ALL
    SELECT
        'blocker',
        'embedding_loaded_chunk_count_match',
        CASE
            WHEN NOT EXISTS (SELECT 1 FROM selected_run) THEN 0
            WHEN (SELECT actual_chunk_count FROM actual_stats) = (SELECT expected_chunk_count FROM expected_stats) THEN 0
            ELSE 1
        END,
        jsonb_build_object(
            'loaded', (SELECT actual_chunk_count FROM actual_stats),
            'expected', (SELECT expected_chunk_count FROM expected_stats)
        )
    UNION ALL
    SELECT
        'blocker',
        'embedding_unknown_chunk_ids',
        count(*)::bigint,
        jsonb_build_object('sample_chunks', coalesce(jsonb_agg(chunk_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT chunk_id, row_number() OVER (ORDER BY chunk_id) AS row_number
        FROM unknown_chunk_ids
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'embedding_missing_chunk_ids',
        count(*)::bigint,
        jsonb_build_object('sample_chunks', coalesce(jsonb_agg(chunk_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT chunk_id, row_number() OVER (ORDER BY chunk_id) AS row_number
        FROM missing_chunk_ids
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'embedding_dimension_mismatch',
        count(*)::bigint,
        jsonb_build_object('sample_chunks', coalesce(jsonb_agg(chunk_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT chunk_id, row_number() OVER (ORDER BY chunk_id) AS row_number
        FROM dimension_mismatch
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'embedding_text_hash_mismatch',
        count(*)::bigint,
        jsonb_build_object('sample_chunks', coalesce(jsonb_agg(chunk_id) FILTER (WHERE row_number <= 5), '[]'::jsonb))
    FROM (
        SELECT chunk_id, row_number() OVER (ORDER BY chunk_id) AS row_number
        FROM hash_mismatch
    ) sampled
) findings
ORDER BY
    CASE severity WHEN 'blocker' THEN 0 ELSE 1 END,
    check_name;
$$;

CREATE OR REPLACE FUNCTION rag.can_promote_embedding_run(p_embedding_run_id uuid)
RETURNS boolean
LANGUAGE sql
AS $$
SELECT NOT EXISTS (
    SELECT 1
    FROM rag.review_embedding_run(p_embedding_run_id)
    WHERE severity = 'blocker'
      AND finding_count > 0
);
$$;

CREATE OR REPLACE FUNCTION rag.promote_embedding_run(p_embedding_run_id uuid)
RETURNS void
LANGUAGE plpgsql
AS $$
DECLARE
    selected_model text;
    selected_source_run uuid;
    selected_dimensions integer;
    selected_distance_metric text;
BEGIN
    SELECT model_name, source_ingestion_run_id, dimensions, distance_metric
    INTO selected_model, selected_source_run, selected_dimensions, selected_distance_metric
    FROM rag.embedding_runs
    WHERE embedding_run_id = p_embedding_run_id;

    IF selected_model IS NULL THEN
        RAISE EXCEPTION 'Embedding run % does not exist.', p_embedding_run_id;
    END IF;

    IF NOT rag.can_promote_embedding_run(p_embedding_run_id) THEN
        RAISE EXCEPTION 'Embedding run % failed blocker checks and cannot be promoted.', p_embedding_run_id;
    END IF;

    UPDATE rag.embedding_runs
    SET status = 'superseded'
    WHERE status = 'promoted'
      AND model_name = selected_model
      AND embedding_run_id <> p_embedding_run_id;

    DELETE FROM rag.chunk_embeddings
    WHERE model_name = selected_model;

    INSERT INTO rag.chunk_embeddings (
        chunk_id,
        model_name,
        embedding_run_id,
        source_ingestion_run_id,
        distance_metric,
        dimensions,
        embedding_text_hash,
        embedding
    )
    SELECT
        s.chunk_id,
        selected_model,
        p_embedding_run_id,
        selected_source_run,
        selected_distance_metric,
        selected_dimensions,
        s.embedding_text_hash,
        s.embedding
    FROM rag.staging_chunk_embeddings s
    JOIN rag.chunks c
      ON c.chunk_id = s.chunk_id
     AND c.source_run_id = selected_source_run
    WHERE s.embedding_run_id = p_embedding_run_id;

    UPDATE rag.embedding_runs
    SET status = 'promoted',
        promoted_at = now()
    WHERE embedding_run_id = p_embedding_run_id;
END;
$$;

CREATE OR REPLACE FUNCTION rag.review_active_embeddings()
RETURNS TABLE (
    severity text,
    check_name text,
    finding_count bigint,
    detail jsonb
)
LANGUAGE sql
AS $$
WITH active_hash_mismatch AS (
    SELECT ce.chunk_id, ce.model_name
    FROM rag.chunk_embeddings ce
    JOIN rag.chunks c
      ON c.chunk_id = ce.chunk_id
    WHERE ce.embedding_text_hash <> c.embedding_text_hash
),
active_source_mismatch AS (
    SELECT ce.chunk_id, ce.model_name
    FROM rag.chunk_embeddings ce
    JOIN rag.chunks c
      ON c.chunk_id = ce.chunk_id
    WHERE ce.source_ingestion_run_id <> c.source_run_id
),
active_dimension_mismatch AS (
    SELECT chunk_id, model_name
    FROM rag.chunk_embeddings
    WHERE vector_dims(embedding) <> dimensions
)
SELECT *
FROM (
    SELECT
        'blocker'::text AS severity,
        'active_embedding_text_hash_mismatch'::text AS check_name,
        count(*)::bigint AS finding_count,
        jsonb_build_object(
            'sample_rows',
            coalesce(jsonb_agg(jsonb_build_object('chunk_id', chunk_id, 'model_name', model_name)) FILTER (WHERE row_number <= 5), '[]'::jsonb)
        ) AS detail
    FROM (
        SELECT chunk_id, model_name, row_number() OVER (ORDER BY model_name, chunk_id) AS row_number
        FROM active_hash_mismatch
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'active_embedding_source_run_mismatch',
        count(*)::bigint,
        jsonb_build_object(
            'sample_rows',
            coalesce(jsonb_agg(jsonb_build_object('chunk_id', chunk_id, 'model_name', model_name)) FILTER (WHERE row_number <= 5), '[]'::jsonb)
        )
    FROM (
        SELECT chunk_id, model_name, row_number() OVER (ORDER BY model_name, chunk_id) AS row_number
        FROM active_source_mismatch
    ) sampled
    UNION ALL
    SELECT
        'blocker',
        'active_embedding_dimension_mismatch',
        count(*)::bigint,
        jsonb_build_object(
            'sample_rows',
            coalesce(jsonb_agg(jsonb_build_object('chunk_id', chunk_id, 'model_name', model_name)) FILTER (WHERE row_number <= 5), '[]'::jsonb)
        )
    FROM (
        SELECT chunk_id, model_name, row_number() OVER (ORDER BY model_name, chunk_id) AS row_number
        FROM active_dimension_mismatch
    ) sampled
) findings
ORDER BY
    CASE severity WHEN 'blocker' THEN 0 ELSE 1 END,
    check_name;
$$;
