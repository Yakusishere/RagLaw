from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import error, request


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build real embeddings JSONL from chunks JSONL using the OpenAI Embeddings API."
    )
    parser.add_argument(
        "--chunks",
        default="build/ingestion/chunks.jsonl",
        help="Path to chunks JSONL.",
    )
    parser.add_argument(
        "--output",
        default="build/embeddings/openai_embeddings.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--model",
        default="text-embedding-3-small",
        help="OpenAI embedding model name.",
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        default=0,
        help="Optional output dimensions. Only supported on text-embedding-3 models. Use 0 to omit.",
    )
    parser.add_argument(
        "--enabled-only",
        action="store_true",
        help="Only generate embeddings for enabled_for_retrieval=true chunks.",
    )
    parser.add_argument(
        "--max-batch-items",
        type=int,
        default=64,
        help="Maximum number of texts per embeddings request.",
    )
    parser.add_argument(
        "--max-batch-chars",
        type=int,
        default=60000,
        help="Conservative per-request character budget used to avoid oversized batches without a tokenizer dependency.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=120,
        help="HTTP timeout per request.",
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Maximum retry attempts for transient API errors.",
    )
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional OpenAI-compatible base URL. Defaults to OPENAI_BASE_URL or https://api.openai.com/v1.",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="Optional API key. Defaults to OPENAI_API_KEY.",
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


def batch_rows(rows: list[dict[str, Any]], max_items: int, max_chars: int) -> list[list[dict[str, Any]]]:
    batches: list[list[dict[str, Any]]] = []
    current_batch: list[dict[str, Any]] = []
    current_chars = 0

    for row in rows:
        text = row["embedding_text"]
        text_chars = len(text)
        if current_batch and (
            len(current_batch) >= max_items or current_chars + text_chars > max_chars
        ):
            batches.append(current_batch)
            current_batch = []
            current_chars = 0

        current_batch.append(row)
        current_chars += text_chars

    if current_batch:
        batches.append(current_batch)

    return batches


def build_payload(model: str, dimensions: int, texts: list[str]) -> bytes:
    payload: dict[str, Any] = {
        "input": texts,
        "model": model,
        "encoding_format": "float",
    }
    if dimensions > 0:
        if not model.startswith("text-embedding-3"):
            raise ValueError("The dimensions parameter is only supported on text-embedding-3 models.")
        payload["dimensions"] = dimensions
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def post_embeddings(
    url: str,
    api_key: str,
    payload: bytes,
    timeout_seconds: int,
    max_retries: int,
) -> dict[str, Any]:
    last_error: Exception | None = None
    for attempt in range(max_retries):
        req = request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:
                body = response.read().decode("utf-8")
            return json.loads(body)
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            retryable = exc.code in {408, 409, 429, 500, 502, 503, 504}
            last_error = RuntimeError(f"OpenAI API HTTP {exc.code}: {body}")
            if not retryable or attempt == max_retries - 1:
                raise last_error
            time.sleep(min(2**attempt, 10))
        except error.URLError as exc:
            last_error = RuntimeError(f"OpenAI API connection failed: {exc}")
            if attempt == max_retries - 1:
                raise last_error
            time.sleep(min(2**attempt, 10))

    if last_error is not None:
        raise last_error
    raise RuntimeError("OpenAI embeddings request failed without an explicit error.")


def main() -> None:
    args = parse_args()
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise RuntimeError("Missing OpenAI API key. Pass --api-key or set OPENAI_API_KEY.")

    base_url = (
        args.base_url
        or os.environ.get("OPENAI_BASE_URL", "")
        or "https://api.openai.com/v1"
    ).rstrip("/")
    embeddings_url = f"{base_url}/embeddings"

    chunks_path = Path(args.chunks).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(chunks_path)
    if args.enabled_only:
        rows = [row for row in rows if row.get("enabled_for_retrieval", False)]
    if not rows:
        raise RuntimeError("No chunk rows selected for embedding generation.")

    batches = batch_rows(rows, args.max_batch_items, args.max_batch_chars)

    output_rows: list[dict[str, Any]] = []
    request_count = 0
    prompt_tokens = 0

    for batch in batches:
        texts = [row["embedding_text"] for row in batch]
        payload = build_payload(args.model, args.dimensions, texts)
        response = post_embeddings(
            url=embeddings_url,
            api_key=api_key,
            payload=payload,
            timeout_seconds=args.timeout_seconds,
            max_retries=args.max_retries,
        )
        data = response.get("data", [])
        if len(data) != len(batch):
            raise RuntimeError(
                f"Embedding response row count mismatch: expected {len(batch)}, got {len(data)}."
            )

        for row, embedding_row in zip(batch, data):
            embedding = embedding_row.get("embedding")
            if not isinstance(embedding, list) or not embedding:
                raise RuntimeError(f"Invalid embedding payload for chunk {row['chunk_id']}.")
            output_rows.append(
                {
                    "chunk_id": row["chunk_id"],
                    "embedding_text_hash": sha256_text(row["embedding_text"]),
                    "embedding": embedding,
                }
            )

        usage = response.get("usage", {})
        prompt_tokens += int(usage.get("prompt_tokens", 0))
        request_count += 1

    with output_path.open("w", encoding="utf-8") as handle:
        for row in output_rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")

    actual_dimensions = len(output_rows[0]["embedding"]) if output_rows else 0
    print(
        json.dumps(
            {
                "output": str(output_path),
                "model": args.model,
                "dimensions": actual_dimensions,
                "row_count": len(output_rows),
                "request_count": request_count,
                "prompt_tokens": prompt_tokens,
                "base_url": base_url,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
