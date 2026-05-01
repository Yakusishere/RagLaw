from __future__ import annotations

import argparse
import json
import re
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET


W_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
HEADING_NUM = r"[一二三四五六七八九十百千万零〇两0-9]+"
PART_RE = re.compile(rf"^(第{HEADING_NUM}编)\s*(.*)$")
CHAPTER_RE = re.compile(rf"^(第{HEADING_NUM}章)\s*(.*)$")
SECTION_RE = re.compile(rf"^(第{HEADING_NUM}节)\s*(.*)$")
ARTICLE_RE = re.compile(rf"^(第{HEADING_NUM}条)\s*(.*)$")
TOC_LINE_RE = re.compile(r"^目\s*录$")
HEADING_LINE_RE = re.compile(rf"^第{HEADING_NUM}[编章节]\s*.*$")
SPLIT_BEFORE_HEADING_RE = re.compile(rf"[ \u3000]{{2,}}(?=第{HEADING_NUM}[编章节条])")


@dataclass
class ManifestRecord:
    document_id: str
    file_path: str
    title: str
    canonical_title: str
    doc_type: str
    source_name: str
    source_url: str
    effective_date: str
    version_note: str
    is_canonical: bool
    enabled_for_retrieval: bool
    subset_of: str | None
    tags: list[str] = field(default_factory=list)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Parse curated DOCX legal materials into document/chunk JSONL artifacts."
    )
    parser.add_argument(
        "--manifest",
        default="data/manifest.jsonl",
        help="Path to manifest JSONL file.",
    )
    parser.add_argument(
        "--root-dir",
        default=".",
        help="Repository root used to resolve manifest file paths.",
    )
    parser.add_argument(
        "--output-dir",
        default="build/ingestion",
        help="Directory for generated JSONL artifacts.",
    )
    return parser.parse_args()


def load_manifest(manifest_path: Path) -> list[ManifestRecord]:
    records: list[ManifestRecord] = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            payload = json.loads(line)
            try:
                records.append(ManifestRecord(**payload))
            except TypeError as exc:
                raise ValueError(
                    f"Invalid manifest record at line {line_no}: {exc}"
                ) from exc
    if not records:
        raise ValueError(f"No records found in manifest: {manifest_path}")
    return records


def read_docx_lines(docx_path: Path) -> list[str]:
    with zipfile.ZipFile(docx_path) as archive:
        xml_bytes = archive.read("word/document.xml")
    root = ET.fromstring(xml_bytes)

    lines: list[str] = []
    for paragraph in root.findall(".//w:body/w:p", W_NS):
        pieces = []
        for node in paragraph.findall(".//w:t", W_NS):
            if node.text:
                pieces.append(node.text)
        line = "".join(pieces).strip()
        if line:
            lines.append(line)
    return lines


def normalize_line(line: str) -> str:
    cleaned = line.replace("\xa0", " ")
    cleaned = re.sub(r"[ \t\u3000]+", " ", cleaned)
    return cleaned.strip()


def explode_compound_lines(lines: list[str]) -> list[str]:
    expanded: list[str] = []
    for line in lines:
        exploded = SPLIT_BEFORE_HEADING_RE.sub("\n", line)
        for part in exploded.splitlines():
            normalized = normalize_line(part)
            if normalized:
                expanded.append(normalized)
    return expanded


def compact_for_compare(line: str) -> str:
    return re.sub(r"\s+", "", line)


def remove_table_of_contents(lines: list[str]) -> list[str]:
    toc_index = next(
        (
            idx
            for idx, line in enumerate(lines)
            if TOC_LINE_RE.match(compact_for_compare(line))
        ),
        None,
    )
    if toc_index is None:
        return lines

    first_heading_index = next(
        (
            idx
            for idx in range(toc_index + 1, len(lines))
            if HEADING_LINE_RE.match(lines[idx])
        ),
        None,
    )
    if first_heading_index is None:
        return [line for idx, line in enumerate(lines) if idx != toc_index]

    first_heading = compact_for_compare(lines[first_heading_index])
    second_heading_index = next(
        (
            idx
            for idx in range(first_heading_index + 1, len(lines))
            if compact_for_compare(lines[idx]) == first_heading
        ),
        None,
    )
    if second_heading_index is None:
        return [line for idx, line in enumerate(lines) if idx != toc_index]

    return lines[:toc_index] + lines[second_heading_index:]


def chinese_numeral_to_int(text: str) -> int | None:
    if text.isdigit():
        return int(text)

    mapping = {
        "零": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}

    total = 0
    section = 0
    number = 0

    for char in text:
        if char in mapping:
            number = mapping[char]
            continue
        if char in units:
            unit = units[char]
            if unit == 10000:
                section = (section + max(number, 1)) * unit
                total += section
                section = 0
                number = 0
                continue
            section += max(number, 1) * unit
            number = 0
            continue
        return None

    return total + section + number


def article_to_int(article_no: str) -> int | None:
    raw = article_no.removeprefix("第").removesuffix("条")
    return chinese_numeral_to_int(raw)


def join_non_empty(parts: list[str]) -> str:
    return "\n".join(part for part in parts if part)


def parse_law_or_rule_chunks(
    record: ManifestRecord, clean_lines: list[str]
) -> tuple[list[dict[str, Any]], list[str]]:
    chunks: list[dict[str, Any]] = []
    warnings: list[str] = []

    current_part: str | None = None
    current_chapter: str | None = None
    current_section: str | None = None
    current_article_no: str | None = None
    current_article_lines: list[str] = []

    def flush_article() -> None:
        nonlocal current_article_no, current_article_lines
        if current_article_no is None:
            return
        article_body = "\n".join(line for line in current_article_lines if line).strip()
        article_number = article_to_int(current_article_no)
        chunk_order = len(chunks) + 1
        chunk_text = (
            f"{current_article_no} {article_body}".strip()
            if article_body
            else current_article_no
        )
        embedding_text = join_non_empty(
            [
                record.title,
                current_part or "",
                current_chapter or "",
                current_section or "",
                chunk_text,
            ]
        )
        chunks.append(
            {
                "chunk_id": f"{record.document_id}:article:{chunk_order:04d}",
                "document_id": record.document_id,
                "doc_type": record.doc_type,
                "chunk_type": "article",
                "chunk_order": chunk_order,
                "title": record.title,
                "canonical_title": record.canonical_title,
                "part_title": current_part,
                "chapter_title": current_chapter,
                "section_title": current_section,
                "article_no": current_article_no,
                "article_no_int": article_number,
                "chunk_text": chunk_text,
                "embedding_text": embedding_text,
                "search_text": embedding_text,
                "citation_label": f"《{record.canonical_title}》{current_article_no}",
                "effective_date": record.effective_date,
                "source_name": record.source_name,
                "source_url": record.source_url,
                "tags": record.tags,
                "is_canonical": record.is_canonical,
                "enabled_for_retrieval": record.enabled_for_retrieval,
                "subset_of": record.subset_of,
                "canonical_key": (
                    f"{record.canonical_title}#{article_number or current_article_no}"
                    f"#{record.effective_date}"
                ),
            }
        )
        current_article_no = None
        current_article_lines = []

    for line in clean_lines:
        part_match = PART_RE.match(line)
        chapter_match = CHAPTER_RE.match(line)
        section_match = SECTION_RE.match(line)
        article_match = ARTICLE_RE.match(line)

        if part_match:
            flush_article()
            current_part = line
            current_chapter = None
            current_section = None
            continue
        if chapter_match:
            flush_article()
            current_chapter = line
            current_section = None
            continue
        if section_match:
            flush_article()
            current_section = line
            continue
        if article_match:
            flush_article()
            current_article_no = article_match.group(1)
            article_start = article_match.group(2).strip()
            current_article_lines = [article_start] if article_start else []
            continue
        if current_article_no is not None:
            current_article_lines.append(line)

    flush_article()

    if not chunks:
        warnings.append("No article chunks parsed from cleaned text.")
    return chunks, warnings


def parse_generic_document_chunk(
    record: ManifestRecord, clean_text: str
) -> tuple[list[dict[str, Any]], list[str]]:
    if not clean_text:
        return [], ["No clean text available for document-level chunk."]

    chunk = {
        "chunk_id": f"{record.document_id}:document:0001",
        "document_id": record.document_id,
        "doc_type": record.doc_type,
        "chunk_type": "document",
        "chunk_order": 1,
        "title": record.title,
        "canonical_title": record.canonical_title,
        "part_title": None,
        "chapter_title": None,
        "section_title": None,
        "article_no": None,
        "article_no_int": None,
        "chunk_text": clean_text,
        "embedding_text": join_non_empty([record.title, clean_text]),
        "search_text": join_non_empty([record.title, clean_text]),
        "citation_label": f"《{record.canonical_title}》",
        "effective_date": record.effective_date,
        "source_name": record.source_name,
        "source_url": record.source_url,
        "tags": record.tags,
        "is_canonical": record.is_canonical,
        "enabled_for_retrieval": record.enabled_for_retrieval,
        "subset_of": record.subset_of,
        "canonical_key": f"{record.canonical_title}#document#{record.effective_date}",
    }
    return [chunk], []


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False))
            handle.write("\n")


def main() -> None:
    args = parse_args()
    manifest_path = Path(args.manifest).resolve()
    root_dir = Path(args.root_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records = load_manifest(manifest_path)

    documents_output: list[dict[str, Any]] = []
    chunks_output: list[dict[str, Any]] = []
    warnings_by_document: dict[str, list[str]] = {}

    for record in records:
        docx_path = (root_dir / record.file_path).resolve()
        if not docx_path.exists():
            raise FileNotFoundError(f"Missing material file: {docx_path}")

        raw_lines = read_docx_lines(docx_path)
        exploded_lines = explode_compound_lines(raw_lines)
        clean_lines = remove_table_of_contents(exploded_lines)

        raw_text = "\n".join(normalize_line(line) for line in raw_lines if normalize_line(line))
        clean_text = "\n".join(clean_lines)

        if record.doc_type in {"law", "rule"}:
            chunks, parse_warnings = parse_law_or_rule_chunks(record, clean_lines)
        else:
            chunks, parse_warnings = parse_generic_document_chunk(record, clean_text)

        warnings_by_document[record.document_id] = parse_warnings

        documents_output.append(
            {
                "document_id": record.document_id,
                "title": record.title,
                "canonical_title": record.canonical_title,
                "doc_type": record.doc_type,
                "source_name": record.source_name,
                "source_url": record.source_url,
                "effective_date": record.effective_date,
                "version_note": record.version_note,
                "file_path": record.file_path,
                "is_canonical": record.is_canonical,
                "enabled_for_retrieval": record.enabled_for_retrieval,
                "subset_of": record.subset_of,
                "tags": record.tags,
                "raw_text": raw_text,
                "clean_text": clean_text,
                "paragraph_count": len(raw_lines),
                "clean_line_count": len(clean_lines),
                "chunk_count": len(chunks),
                "warnings": parse_warnings,
            }
        )
        chunks_output.extend(chunks)

    canonical_counter_all = Counter(chunk["canonical_key"] for chunk in chunks_output)
    canonical_counter_enabled = Counter(
        chunk["canonical_key"]
        for chunk in chunks_output
        if chunk["enabled_for_retrieval"]
    )
    duplicate_canonical_keys_all = {
        key: count for key, count in canonical_counter_all.items() if count > 1
    }
    duplicate_canonical_keys_enabled = {
        key: count for key, count in canonical_counter_enabled.items() if count > 1
    }

    stats = {
        "document_count": len(documents_output),
        "chunk_count": len(chunks_output),
        "documents_enabled_for_retrieval": sum(
            1 for document in documents_output if document["enabled_for_retrieval"]
        ),
        "chunks_enabled_for_retrieval": sum(
            1 for chunk in chunks_output if chunk["enabled_for_retrieval"]
        ),
        "doc_type_counts": dict(Counter(doc["doc_type"] for doc in documents_output)),
        "duplicate_canonical_keys_all": duplicate_canonical_keys_all,
        "duplicate_canonical_keys_enabled": duplicate_canonical_keys_enabled,
        "warnings_by_document": warnings_by_document,
    }

    write_jsonl(output_dir / "documents.jsonl", documents_output)
    write_jsonl(output_dir / "chunks.jsonl", chunks_output)
    with (output_dir / "stats.json").open("w", encoding="utf-8") as handle:
        json.dump(stats, handle, ensure_ascii=False, indent=2)

    print(
        json.dumps(
            {
                "document_count": stats["document_count"],
                "chunk_count": stats["chunk_count"],
                "output_dir": str(output_dir),
                "duplicate_canonical_keys_all": len(duplicate_canonical_keys_all),
                "duplicate_canonical_keys_enabled": len(duplicate_canonical_keys_enabled),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
