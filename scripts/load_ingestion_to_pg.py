from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load generated ingestion JSONL into PostgreSQL staging tables via docker exec."
    )
    parser.add_argument("--container", default="law-helper-pg", help="Docker container name.")
    parser.add_argument("--db-user", default="law", help="PostgreSQL user inside the container.")
    parser.add_argument("--db-name", default="law_helper", help="Database name inside the container.")
    parser.add_argument(
        "--manifest",
        default="data/manifest.jsonl",
        help="Manifest path recorded in the ingestion run metadata.",
    )
    parser.add_argument(
        "--documents",
        default="build/ingestion/documents.jsonl",
        help="Path to documents JSONL.",
    )
    parser.add_argument(
        "--chunks",
        default="build/ingestion/chunks.jsonl",
        help="Path to chunks JSONL.",
    )
    parser.add_argument(
        "--stats",
        default="build/ingestion/stats.json",
        help="Path to stats JSON.",
    )
    parser.add_argument(
        "--run-label",
        default="manual-load",
        help="User-facing label for this ingestion run.",
    )
    parser.add_argument(
        "--promote-if-clean",
        action="store_true",
        help="Promote the run immediately if blocker checks pass.",
    )
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize_scalar(value: Any) -> Any:
    if value == "":
        return None
    return value


def prepare_documents(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["source_url"] = normalize_scalar(item.get("source_url"))
        item["effective_date"] = normalize_scalar(item.get("effective_date"))
        item["subset_of"] = normalize_scalar(item.get("subset_of"))
        item["tags"] = item.get("tags") or []
        item["warnings"] = item.get("warnings") or []
        item["clean_text_hash"] = sha256_text(item["clean_text"])
        prepared.append(item)
    return prepared


def prepare_chunks(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    prepared: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["source_url"] = normalize_scalar(item.get("source_url"))
        item["effective_date"] = normalize_scalar(item.get("effective_date"))
        item["subset_of"] = normalize_scalar(item.get("subset_of"))
        item["part_title"] = normalize_scalar(item.get("part_title"))
        item["chapter_title"] = normalize_scalar(item.get("chapter_title"))
        item["section_title"] = normalize_scalar(item.get("section_title"))
        item["article_no"] = normalize_scalar(item.get("article_no"))
        item["article_no_int"] = item.get("article_no_int")
        item["tags"] = item.get("tags") or []
        item["embedding_text_hash"] = sha256_text(item["embedding_text"])
        item["chunk_text_hash"] = sha256_text(item["chunk_text"])
        prepared.append(item)
    return prepared


def dollar_quote(text: str, tag_prefix: str) -> str:
    tag = f"{tag_prefix}_{uuid.uuid4().hex}"
    return f"${tag}${text}${tag}$"


def build_document_insert_sql(run_id: str, batch: list[dict[str, Any]]) -> str:
    payload = json.dumps(batch, ensure_ascii=False)
    return f"""
WITH src AS (
    SELECT *
    FROM jsonb_to_recordset({dollar_quote(payload, 'docs')}::jsonb) AS x(
        document_id text,
        title text,
        canonical_title text,
        doc_type text,
        source_name text,
        source_url text,
        effective_date text,
        version_note text,
        file_path text,
        is_canonical boolean,
        enabled_for_retrieval boolean,
        subset_of text,
        tags jsonb,
        raw_text text,
        clean_text text,
        paragraph_count integer,
        clean_line_count integer,
        chunk_count integer,
        warnings jsonb,
        clean_text_hash text
    )
)
INSERT INTO rag.staging_documents (
    run_id,
    document_id,
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
    '{run_id}'::uuid,
    document_id,
    title,
    canonical_title,
    doc_type,
    source_name,
    source_url,
    NULLIF(effective_date, '')::date,
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
FROM src;
""".strip()


def build_chunk_insert_sql(run_id: str, batch: list[dict[str, Any]]) -> str:
    payload = json.dumps(batch, ensure_ascii=False)
    return f"""
WITH src AS (
    SELECT *
    FROM jsonb_to_recordset({dollar_quote(payload, 'chunks')}::jsonb) AS x(
        chunk_id text,
        document_id text,
        doc_type text,
        chunk_type text,
        chunk_order integer,
        title text,
        canonical_title text,
        part_title text,
        chapter_title text,
        section_title text,
        article_no text,
        article_no_int integer,
        chunk_text text,
        embedding_text_hash text,
        embedding_text text,
        search_text text,
        citation_label text,
        effective_date text,
        source_name text,
        source_url text,
        tags jsonb,
        is_canonical boolean,
        enabled_for_retrieval boolean,
        subset_of text,
        canonical_key text,
        chunk_text_hash text
    )
)
INSERT INTO rag.staging_chunks (
    run_id,
    chunk_id,
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
    embedding_text_hash,
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
    '{run_id}'::uuid,
    chunk_id,
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
    embedding_text_hash,
    embedding_text,
    search_text,
    citation_label,
    NULLIF(effective_date, '')::date,
    source_name,
    source_url,
    tags,
    is_canonical,
    enabled_for_retrieval,
    subset_of,
    canonical_key,
    chunk_text_hash
FROM src;
""".strip()


def run_psql(container: str, db_user: str, db_name: str, sql: str) -> subprocess.CompletedProcess[str]:
    command = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        db_user,
        "-d",
        db_name,
        "-f",
        "-",
    ]
    try:
        return subprocess.run(
            command,
            input=sql.encode("utf-8"),
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace").strip()
        stdout = exc.stdout.decode("utf-8", errors="replace").strip()
        message = stderr or stdout or str(exc)
        raise RuntimeError(message) from exc


def batched(rows: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [rows[idx : idx + batch_size] for idx in range(0, len(rows), batch_size)]


def load_run(args: argparse.Namespace) -> str:
    manifest_path = Path(args.manifest).resolve()
    documents_path = Path(args.documents).resolve()
    chunks_path = Path(args.chunks).resolve()
    stats_path = Path(args.stats).resolve()

    documents = prepare_documents(load_jsonl(documents_path))
    chunks = prepare_chunks(load_jsonl(chunks_path))
    stats = json.loads(stats_path.read_text(encoding="utf-8"))

    run_id = str(uuid.uuid4())
    statements: list[str] = [
        "BEGIN;",
        f"""
INSERT INTO rag.ingestion_runs (
    run_id,
    run_label,
    manifest_path,
    documents_path,
    chunks_path,
    source_stats,
    status
)
VALUES (
    '{run_id}'::uuid,
    {dollar_quote(args.run_label, 'run_label')},
    {dollar_quote(str(manifest_path), 'manifest_path')},
    {dollar_quote(str(documents_path), 'documents_path')},
    {dollar_quote(str(chunks_path), 'chunks_path')},
    {dollar_quote(json.dumps(stats, ensure_ascii=False), 'source_stats')}::jsonb,
    'loaded'
);
""".strip(),
    ]

    for batch in batched(documents, 25):
        statements.append(build_document_insert_sql(run_id, batch))

    for batch in batched(chunks, 100):
        statements.append(build_chunk_insert_sql(run_id, batch))

    statements.append("COMMIT;")

    run_psql(args.container, args.db_user, args.db_name, "\n".join(statements))
    return run_id


def print_review(args: argparse.Namespace, run_id: str) -> None:
    sql = f"""
SELECT json_build_object(
    'severity', severity,
    'check_name', check_name,
    'finding_count', finding_count,
    'detail', detail
)
FROM rag.review_findings('{run_id}'::uuid);
""".strip()
    result = run_psql(args.container, args.db_user, args.db_name, sql)
    print(result.stdout.decode("utf-8", errors="replace").strip())


def promote_run(args: argparse.Namespace, run_id: str) -> None:
    sql = f"SELECT rag.promote_run('{run_id}'::uuid);"
    run_psql(args.container, args.db_user, args.db_name, sql)


def main() -> None:
    args = parse_args()
    run_id = load_run(args)
    print(json.dumps({"run_id": run_id, "status": "loaded"}, ensure_ascii=False))
    print_review(args, run_id)
    if args.promote_if_clean:
        promote_run(args, run_id)
        print(json.dumps({"run_id": run_id, "status": "promoted"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
