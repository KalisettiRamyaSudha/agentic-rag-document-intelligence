"""Build canonical document and section-aware chunk records."""

from __future__ import annotations

import re
from pathlib import Path

from document_intelligence.ids import (
    content_checksum,
    make_chunk_id,
    make_document_id,
    normalize_source_uri,
    normalize_text,
)
from document_intelligence.models import ChunkMetadata, ChunkRecord, DocumentRecord

SECTION_PATTERN = re.compile(r"^SECTION\s+(\d+):\s*(.+?)\s*$")
POLICY_PERIOD_PATTERN = re.compile(r"Policy Period:\s*([^\n]+?)\s+to\s+[^\n]+")


def load_document(
    source_path: str | Path,
    *,
    source_root: str | Path | None = None,
    version: str = "v1",
) -> DocumentRecord:
    """Load a source text file into a canonical document record."""
    path = Path(source_path)
    text = normalize_text(path.read_text(encoding="utf-8"))
    source_uri = normalize_source_uri(path, source_root)
    checksum = content_checksum(text)
    document_id = make_document_id(source_uri, version)
    return DocumentRecord(
        document_id=document_id,
        source_uri=source_uri,
        version=version,
        text=text,
        content_checksum=checksum,
        metadata={
            "source_type": "text",
            "loader": "canonical_section_loader",
            "checksum_algorithm": "sha256",
        },
    )


def parse_section_chunks(document: DocumentRecord) -> list[ChunkRecord]:
    """Parse a document into chunks whose boundaries follow SECTION headers."""
    lines = document.text.splitlines()
    section_starts: list[tuple[int, int, str]] = []

    for line_number, line in enumerate(lines, start=1):
        match = SECTION_PATTERN.match(line)
        if match:
            section_starts.append((line_number, int(match.group(1)), match.group(2)))

    if not section_starts:
        fallback_chunks = [_make_chunk(document, 0, 1, max(len(lines), 1), None, None)]
        _ensure_unique_chunk_ids(fallback_chunks)
        return fallback_chunks

    chunks: list[ChunkRecord] = []
    for chunk_index, (start_line, section_number, section_title) in enumerate(section_starts):
        if chunk_index + 1 < len(section_starts):
            end_line = section_starts[chunk_index + 1][0] - 1
        else:
            end_line = len(lines)
        chunks.append(
            _make_chunk(
                document,
                chunk_index,
                start_line,
                end_line,
                section_number,
                section_title,
            )
        )
    _ensure_unique_chunk_ids(chunks)
    return chunks


def ingest_documents(
    source_path: str | Path,
    *,
    source_root: str | Path | None = None,
    version: str = "v1",
) -> tuple[DocumentRecord, list[ChunkRecord]]:
    """Load and parse a source file into canonical records."""
    document = load_document(source_path, source_root=source_root, version=version)
    chunks = parse_section_chunks(document)
    return document, chunks


def _make_chunk(
    document: DocumentRecord,
    chunk_index: int,
    start_line: int,
    end_line: int,
    section_number: int | None,
    section_title: str | None,
) -> ChunkRecord:
    lines = document.text.splitlines()
    text = normalize_text("\n".join(lines[start_line - 1 : end_line]))
    if section_number is None:
        section_number = 1
    if section_title is None:
        section_title = "FULL DOCUMENT"
    metadata = ChunkMetadata(
        source_uri=document.source_uri,
        policy_type=_infer_policy_type(section_title),
        section_number=section_number,
        section_title=section_title,
        version=document.version,
        effective_date=_extract_effective_date(text),
        start_line=start_line,
        end_line=end_line,
        content_checksum=content_checksum(text),
    )
    chunk_id = make_chunk_id(document.document_id, chunk_index)
    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document.document_id,
        text=text,
        chunk_index=chunk_index,
        metadata=metadata,
    )


def _ensure_unique_chunk_ids(chunks: list[ChunkRecord]) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for chunk in chunks:
        if chunk.chunk_id in seen:
            duplicates.append(chunk.chunk_id)
        seen.add(chunk.chunk_id)
    if duplicates:
        duplicate_list = ", ".join(sorted(set(duplicates)))
        raise ValueError(f"Duplicate chunk IDs generated: {duplicate_list}")


def _extract_effective_date(text: str) -> str | None:
    match = POLICY_PERIOD_PATTERN.search(text)
    if match:
        return match.group(1).strip()
    return None


def _infer_policy_type(section_title: str) -> str:
    normalized = section_title.upper()
    if (
        "HOMEOWNERS" in normalized
        or normalized.startswith("EXCLUSIONS")
        or "COVERAGE" in normalized
    ):
        return "homeowners"
    if "COMMERCIAL AUTO" in normalized:
        return "commercial_auto"
    if "GENERAL LIABILITY" in normalized:
        return "general_liability"
    if "WORKERS COMPENSATION" in normalized:
        return "workers_compensation"
    if "UMBRELLA" in normalized or "EXCESS" in normalized:
        return "umbrella"
    if "PROFESSIONAL LIABILITY" in normalized or "ERRORS" in normalized:
        return "professional_liability"
    if "BUSINESS OWNERS" in normalized or "BOP" in normalized:
        return "business_owners"
    if "CYBER" in normalized:
        return "cyber_liability"
    if "INLAND MARINE" in normalized or "CONTRACTORS EQUIPMENT" in normalized:
        return "inland_marine"
    if "ENDORSEMENT" in normalized:
        return "endorsement"
    if "CLAIMS" in normalized:
        return "claims"
    return "unknown"
