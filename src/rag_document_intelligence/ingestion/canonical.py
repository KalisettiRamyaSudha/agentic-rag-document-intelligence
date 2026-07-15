"""Build canonical document and section-aware chunk records."""

from __future__ import annotations

import re
from pathlib import Path

from rag_document_intelligence.ids import make_chunk_id, make_document_id, normalize_text
from rag_document_intelligence.models import ChunkMetadata, ChunkRecord, DocumentRecord

SECTION_PATTERN = re.compile(r"^SECTION\s+(\d+):\s*(.+?)\s*$")


def load_document(source_path: str | Path) -> DocumentRecord:
    """Load a source text file into a canonical document record."""
    path = Path(source_path)
    text = normalize_text(path.read_text(encoding="utf-8"))
    source = path.as_posix()
    document_id = make_document_id(source, text)
    return DocumentRecord(
        document_id=document_id,
        source_path=source,
        text=text,
        metadata={"source_type": "text", "loader": "canonical_section_loader"},
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
        return [_make_chunk(document, 0, 1, len(lines), None, None)]

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


def ingest_documents(source_path: str | Path) -> tuple[DocumentRecord, list[ChunkRecord]]:
    """Load and parse a source file into canonical records."""
    document = load_document(source_path)
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
        source_path=document.source_path,
        section_number=section_number,
        section_title=section_title,
        start_line=start_line,
        end_line=end_line,
    )
    chunk_id = make_chunk_id(document.document_id, chunk_index, text)
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
