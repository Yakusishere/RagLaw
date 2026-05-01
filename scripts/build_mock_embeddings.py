from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build deterministic mock embeddings from chunks JSONL for pipeline validation."
    )
    parser.add_argument(
        "--chunks",
        default="build/ingestion/chunks.jsonl",
        help="Path to chunks JSONL.",
    )
    parser.add_argument(
        "--output",
        default="build/embeddings/mock_embeddings.jsonl",
        help="Output JSONL path.",
    )
    parser.add_argument(
        "--dimensions",
        type=int,
        default=16,
        help="Vector dimension for the mock embeddings.",
    )
    parser.add_argument(
        "--enabled-only",
        action="store_true",
        help="Only generate embeddings for enabled_for_retrieval=true chunks.",
    )
    return parser.parse_args()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def mock_embedding(text: str, dimensions: int) -> list[float]:
    values: list[float] = []
    counter = 0
    while len(values) < dimensions:
        digest = hashlib.sha256(f"{counter}:{text}".encode("utf-8")).digest()
        for idx in range(0, len(digest), 4):
            if len(values) >= dimensions:
                break
            chunk = digest[idx : idx + 4]
            raw = int.from_bytes(chunk, byteorder="big", signed=False)
            values.append((raw / 4294967295.0) * 2.0 - 1.0)
        counter += 1

    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return [0.0 for _ in values]
    return [round(value / norm, 8) for value in values]


def main() -> None:
    args = parse_args()
    chunks_path = Path(args.chunks).resolve()
    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = load_jsonl(chunks_path)
    count = 0
    with output_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if args.enabled_only and not row.get("enabled_for_retrieval", False):
                continue
            embedding_text = row["embedding_text"]
            payload = {
                "chunk_id": row["chunk_id"],
                "embedding_text_hash": sha256_text(embedding_text),
                "embedding": mock_embedding(embedding_text, args.dimensions),
            }
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")
            count += 1

    print(
        json.dumps(
            {
                "output": str(output_path),
                "dimensions": args.dimensions,
                "row_count": count,
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
