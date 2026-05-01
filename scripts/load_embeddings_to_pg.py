from __future__ import annotations

import argparse
import json
import subprocess
import uuid
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Load embedding JSONL into PostgreSQL staging tables via docker exec."
    )
    parser.add_argument("--container", default="law-helper-pg", help="Docker container name.")
    parser.add_argument("--db-user", default="law", help="PostgreSQL user inside the container.")
    parser.add_argument("--db-name", default="law_helper", help="Database name inside the container.")
    parser.add_argument(
        "--embeddings",
        default="build/embeddings/mock_embeddings.jsonl",
        help="Path to embeddings JSONL.",
    )
    parser.add_argument("--run-label", default="manual-embedding-load", help="Embedding run label.")
    parser.add_argument("--model-name", required=True, help="Embedding model name.")
    parser.add_argument(
        "--distance-metric",
        default="cosine",
        choices=["cosine", "l2", "ip"],
        help="Distance metric used for retrieval.",
    )
    parser.add_argument(
        "--chunk-scope",
        default="enabled_only",
        choices=["enabled_only", "all_chunks"],
        help="Whether embeddings cover only enabled chunks or all chunks in the source run.",
    )
    parser.add_argument(
        "--source-run-id",
        default="",
        help="Source promoted ingestion run id. If omitted, the script uses the current promoted corpus run.",
    )
    parser.add_argument(
        "--promote-if-clean",
        action="store_true",
        help="Promote the embedding run immediately if blocker checks pass.",
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


def dollar_quote(text: str, tag_prefix: str) -> str:
    tag = f"{tag_prefix}_{uuid.uuid4().hex}"
    return f"${tag}${text}${tag}$"


def run_psql(container: str, db_user: str, db_name: str, sql: str) -> subprocess.CompletedProcess[bytes]:
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


def fetch_scalar(container: str, db_user: str, db_name: str, sql: str) -> str:
    command = [
        "docker",
        "exec",
        "-i",
        container,
        "psql",
        "-At",
        "-v",
        "ON_ERROR_STOP=1",
        "-U",
        db_user,
        "-d",
        db_name,
        "-c",
        sql,
    ]
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except subprocess.CalledProcessError as exc:
        message = exc.stderr.strip() or exc.stdout.strip() or str(exc)
        raise RuntimeError(message) from exc
    return result.stdout.strip()


def current_promoted_run_id(args: argparse.Namespace) -> str:
    sql = """
SELECT run_id
FROM rag.ingestion_runs
WHERE status = 'promoted'
ORDER BY promoted_at DESC NULLS LAST, loaded_at DESC
LIMIT 1;
""".strip()
    run_id = fetch_scalar(args.container, args.db_user, args.db_name, sql)
    if not run_id or run_id == "(0 rows)":
        raise RuntimeError("No promoted ingestion run found in rag.ingestion_runs.")
    return run_id


def batched(rows: list[dict[str, Any]], batch_size: int) -> list[list[dict[str, Any]]]:
    return [rows[idx : idx + batch_size] for idx in range(0, len(rows), batch_size)]


def build_embedding_insert_sql(embedding_run_id: str, batch: list[dict[str, Any]]) -> str:
    payload = json.dumps(batch, ensure_ascii=False)
    return f"""
WITH src AS (
    SELECT *
    FROM jsonb_to_recordset({dollar_quote(payload, 'embedding_rows')}::jsonb) AS x(
        chunk_id text,
        embedding_text_hash text,
        embedding jsonb
    )
)
INSERT INTO rag.staging_chunk_embeddings (
    embedding_run_id,
    chunk_id,
    embedding_text_hash,
    embedding
)
SELECT
    '{embedding_run_id}'::uuid,
    chunk_id,
    embedding_text_hash,
    embedding::text::vector
FROM src;
""".strip()


def load_embedding_run(args: argparse.Namespace) -> str:
    embeddings_path = Path(args.embeddings).resolve()
    rows = load_jsonl(embeddings_path)
    if not rows:
        raise RuntimeError(f"No embedding rows found in {embeddings_path}")

    first_embedding = rows[0].get("embedding")
    if not isinstance(first_embedding, list) or not first_embedding:
        raise RuntimeError("Embedding JSONL rows must contain a non-empty 'embedding' list.")

    dimensions = len(first_embedding)
    for row in rows:
        embedding = row.get("embedding")
        if not isinstance(embedding, list) or len(embedding) != dimensions:
            raise RuntimeError("All embeddings in a run must have the same dimensions.")
        if not row.get("chunk_id"):
            raise RuntimeError("Each embedding row must include 'chunk_id'.")
        if not row.get("embedding_text_hash"):
            raise RuntimeError("Each embedding row must include 'embedding_text_hash'.")

    source_run_id = args.source_run_id or current_promoted_run_id(args)
    embedding_run_id = str(uuid.uuid4())

    statements: list[str] = [
        "BEGIN;",
        f"""
INSERT INTO rag.embedding_runs (
    embedding_run_id,
    run_label,
    source_ingestion_run_id,
    embeddings_path,
    model_name,
    dimensions,
    distance_metric,
    chunk_scope,
    expected_chunk_count,
    status
)
VALUES (
    '{embedding_run_id}'::uuid,
    {dollar_quote(args.run_label, 'embedding_run_label')},
    '{source_run_id}'::uuid,
    {dollar_quote(str(embeddings_path), 'embeddings_path')},
    {dollar_quote(args.model_name, 'model_name')},
    {dimensions},
    {dollar_quote(args.distance_metric, 'distance_metric')},
    {dollar_quote(args.chunk_scope, 'chunk_scope')},
    {len(rows)},
    'loaded'
);
""".strip(),
    ]

    for batch in batched(rows, 100):
        statements.append(build_embedding_insert_sql(embedding_run_id, batch))

    statements.append("COMMIT;")
    run_psql(args.container, args.db_user, args.db_name, "\n".join(statements))
    return embedding_run_id


def print_review(args: argparse.Namespace, embedding_run_id: str) -> None:
    sql = f"""
SELECT json_build_object(
    'severity', severity,
    'check_name', check_name,
    'finding_count', finding_count,
    'detail', detail
)
FROM rag.review_embedding_run('{embedding_run_id}'::uuid);
""".strip()
    result = run_psql(args.container, args.db_user, args.db_name, sql)
    print(result.stdout.decode("utf-8", errors="replace").strip())


def promote_embedding_run(args: argparse.Namespace, embedding_run_id: str) -> None:
    sql = f"SELECT rag.promote_embedding_run('{embedding_run_id}'::uuid);"
    run_psql(args.container, args.db_user, args.db_name, sql)


def main() -> None:
    args = parse_args()
    embedding_run_id = load_embedding_run(args)
    print(json.dumps({"embedding_run_id": embedding_run_id, "status": "loaded"}, ensure_ascii=False))
    print_review(args, embedding_run_id)
    if args.promote_if_clean:
        promote_embedding_run(args, embedding_run_id)
        print(json.dumps({"embedding_run_id": embedding_run_id, "status": "promoted"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
