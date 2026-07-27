"""Build canonical document and section-aware chunk records."""

from __future__ import annotations

import re
from pathlib import Path

from pydantic import TypeAdapter

from document_intelligence.ids import (
    content_checksum,
    make_chunk_id,
    make_document_id,
    normalize_source_uri,
    normalize_text,
)
from document_intelligence.models import (
    ChunkMetadata,
    ChunkRecord,
    DocumentRecord,
    IngestionManifest,
    ManifestDocument,
)

SECTION_PATTERN = re.compile(r"^SECTION\s+(\d+):\s*(.+?)\s*$")
POLICY_PERIOD_PATTERN = re.compile(r"Policy Period:\s*([^\n]+?)\s+to\s+([^\n]+)")
TEXT_EXTENSIONS = {".txt", ".md"}


class EmptyDocumentError(ValueError):
    """Raised when an input document contains no usable text."""


def token_count(text: str) -> int:
    """Count whitespace-delimited tokens for deterministic local subchunking."""
    return len(text.split())


def load_document(
    source_path: str | Path,
    *,
    source_root: str | Path | None = None,
    version: str = "v1",
    title: str | None = None,
    policy_type: str = "unknown",
    effective_date: str | None = None,
    expiration_date: str | None = None,
    source_uri: str | None = None,
) -> DocumentRecord:
    """Load a standalone source text file into a canonical document record."""
    path = Path(source_path)
    text = normalize_text(path.read_text(encoding="utf-8"))
    if not text:
        raise EmptyDocumentError(f"Document is empty or whitespace-only: {path}")

    logical_source_uri = source_uri or normalize_source_uri(path, source_root)
    inferred_effective_date, inferred_expiration_date = _extract_policy_period(text)
    document_id = make_document_id(logical_source_uri, version)
    return DocumentRecord(
        document_id=document_id,
        title=title or path.stem.replace("-", " ").replace("_", " ").title(),
        policy_type=policy_type,
        version=version,
        source_uri=logical_source_uri,
        effective_date=effective_date or inferred_effective_date,
        expiration_date=expiration_date or inferred_expiration_date,
        text=text,
        content_checksum=content_checksum(text),
    )


def parse_section_chunks(document: DocumentRecord, *, max_tokens: int = 220) -> list[ChunkRecord]:
    """Parse a document into section-aware chunks with bounded subchunks."""
    if max_tokens < 1:
        raise ValueError("max_tokens must be greater than zero")
    lines = document.text.splitlines()
    section_starts: list[tuple[int, int, str]] = []

    for line_number, line in enumerate(lines, start=1):
        match = SECTION_PATTERN.match(line)
        if match:
            section_starts.append((line_number, int(match.group(1)), match.group(2)))

    sections: list[tuple[str, int | None, str, int, int]] = []
    if section_starts and section_starts[0][0] > 1:
        sections.append(("PREAMBLE", None, "PREAMBLE", 1, section_starts[0][0] - 1))

    if not section_starts:
        sections.append(("FULL", None, "FULL DOCUMENT", 1, len(lines)))
    else:
        for section_index, (start_line, section_number, section_title) in enumerate(section_starts):
            if section_index + 1 < len(section_starts):
                end_line = section_starts[section_index + 1][0] - 1
            else:
                end_line = len(lines)
            sections.append(
                (
                    f"S{section_number:03d}",
                    section_number,
                    section_title,
                    start_line,
                    end_line,
                )
            )

    chunks: list[ChunkRecord] = []
    for section_key, chunk_section_number, section_title, start_line, end_line in sections:
        section_text = normalize_text("\n".join(lines[start_line - 1 : end_line]))
        if not section_text:
            continue
        chunks.extend(
            _build_section_chunks(
                document,
                section_key,
                chunk_section_number,
                section_title,
                start_line,
                end_line,
                section_text,
                max_tokens,
                len(chunks),
            )
        )

    _ensure_unique_chunk_ids(chunks)
    return chunks


def ingest_document(
    source_path: str | Path,
    *,
    source_root: str | Path | None = None,
    version: str = "v1",
    max_tokens: int = 220,
    title: str | None = None,
    policy_type: str = "unknown",
    effective_date: str | None = None,
    expiration_date: str | None = None,
    source_uri: str | None = None,
) -> tuple[DocumentRecord, list[ChunkRecord]]:
    """Load and parse one standalone source file into canonical records."""
    document = load_document(
        source_path,
        source_root=source_root,
        version=version,
        title=title,
        policy_type=policy_type,
        effective_date=effective_date,
        expiration_date=expiration_date,
        source_uri=source_uri,
    )
    return document, parse_section_chunks(document, max_tokens=max_tokens)


def ingest_collection(
    source: str | Path,
    *,
    source_root: str | Path | None = None,
    version: str = "v1",
    max_tokens: int = 220,
) -> tuple[list[DocumentRecord], list[ChunkRecord]]:
    """Ingest a manifest, directory, or single source file into canonical records."""
    source_path = Path(source)
    if source_path.is_dir():
        return _ingest_directory(
            source_path,
            source_root=source_root,
            version=version,
            max_tokens=max_tokens,
        )
    if source_path.suffix == ".json":
        return _ingest_manifest(
            source_path,
            source_root=source_root,
            version=version,
            max_tokens=max_tokens,
        )
    document, chunks = ingest_document(
        source_path,
        source_root=source_root,
        version=version,
        max_tokens=max_tokens,
    )
    return [document], chunks


# Backward-compatible alias for earlier Phase 1 callers.
def ingest_documents(
    source_path: str | Path,
    *,
    source_root: str | Path | None = None,
    version: str = "v1",
    max_tokens: int = 220,
) -> tuple[DocumentRecord, list[ChunkRecord]]:
    """Load and parse one source file into canonical records."""
    return ingest_document(
        source_path,
        source_root=source_root,
        version=version,
        max_tokens=max_tokens,
    )


def _ingest_directory(
    source_dir: Path,
    *,
    source_root: str | Path | None,
    version: str,
    max_tokens: int,
) -> tuple[list[DocumentRecord], list[ChunkRecord]]:
    documents: list[DocumentRecord] = []
    chunks: list[ChunkRecord] = []
    for path in sorted(p for p in source_dir.rglob("*") if p.suffix in TEXT_EXTENSIONS):
        document, document_chunks = ingest_document(
            path,
            source_root=source_root,
            version=version,
            max_tokens=max_tokens,
        )
        documents.append(document)
        chunks.extend(document_chunks)
    _ensure_unique_document_ids(documents)
    _ensure_unique_chunk_ids(chunks)
    return documents, chunks


def _ingest_manifest(
    manifest_path: Path,
    *,
    source_root: str | Path | None,
    version: str,
    max_tokens: int,
) -> tuple[list[DocumentRecord], list[ChunkRecord]]:
    manifest = IngestionManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    combined_source = (manifest_path.parent / manifest.source_file).resolve()
    combined_text = normalize_text(combined_source.read_text(encoding="utf-8"))
    sections = _section_ranges(combined_text)

    documents: list[DocumentRecord] = []
    chunks: list[ChunkRecord] = []
    for spec in manifest.documents:
        text = _extract_manifest_document_text(combined_text, sections, spec)
        document = load_manifest_document(text, spec, version=version or manifest.version)
        document_chunks = parse_section_chunks(document, max_tokens=max_tokens)
        documents.append(document)
        chunks.extend(document_chunks)

    _ensure_unique_document_ids(documents)
    _ensure_unique_chunk_ids(chunks)
    return documents, chunks


def load_manifest_document(text: str, spec: ManifestDocument, *, version: str) -> DocumentRecord:
    """Build a document record from manifest text and explicit metadata."""
    normalized = normalize_text(text)
    if not normalized:
        raise EmptyDocumentError(f"Document is empty or whitespace-only: {spec.source_uri}")
    document_id = make_document_id(spec.source_uri, version)
    return DocumentRecord(
        document_id=document_id,
        title=spec.title,
        policy_type=spec.policy_type,
        version=version,
        source_uri=spec.source_uri,
        effective_date=spec.effective_date,
        expiration_date=spec.expiration_date,
        text=normalized,
        content_checksum=content_checksum(normalized),
    )


def _section_ranges(text: str) -> dict[int, tuple[int, int]]:
    lines = text.splitlines()
    starts: list[tuple[int, int]] = []
    for line_number, line in enumerate(lines, start=1):
        match = SECTION_PATTERN.match(line)
        if match:
            starts.append((int(match.group(1)), line_number))
    ranges: dict[int, tuple[int, int]] = {}
    for index, (section_number, start_line) in enumerate(starts):
        end_line = starts[index + 1][1] - 1 if index + 1 < len(starts) else len(lines)
        ranges[section_number] = (start_line, end_line)
    return ranges


def _extract_manifest_document_text(
    combined_text: str,
    sections: dict[int, tuple[int, int]],
    spec: ManifestDocument,
) -> str:
    missing = [
        section_number
        for section_number in range(spec.start_section, spec.end_section + 1)
        if section_number not in sections
    ]
    if missing:
        raise ValueError(f"Manifest references missing sections: {missing}")
    lines = combined_text.splitlines()
    start_line = sections[spec.start_section][0]
    end_line = sections[spec.end_section][1]
    return normalize_text("\n".join(lines[start_line - 1 : end_line]))


def _build_section_chunks(
    document: DocumentRecord,
    section_key: str,
    section_number: int | None,
    section_title: str,
    start_line: int,
    end_line: int,
    section_text: str,
    max_tokens: int,
    starting_chunk_index: int,
) -> list[ChunkRecord]:
    tokenized = section_text.split()
    if not tokenized:
        return []
    chunks: list[ChunkRecord] = []
    for subchunk_ordinal, start_token in enumerate(range(0, len(tokenized), max_tokens)):
        chunk_text = " ".join(tokenized[start_token : start_token + max_tokens])
        metadata = ChunkMetadata(
            title=document.title,
            source_uri=document.source_uri,
            policy_type=document.policy_type,
            version=document.version,
            effective_date=document.effective_date,
            expiration_date=document.expiration_date,
            section_key=section_key,
            section_number=section_number,
            section_title=section_title,
            start_line=start_line,
            end_line=end_line,
        )
        chunks.append(
            ChunkRecord(
                chunk_id=make_chunk_id(document.document_id, section_key, subchunk_ordinal),
                document_id=document.document_id,
                text=chunk_text,
                chunk_index=starting_chunk_index + len(chunks),
                subchunk_ordinal=subchunk_ordinal,
                token_count=token_count(chunk_text),
                content_checksum=content_checksum(chunk_text),
                metadata=metadata,
            )
        )
    return chunks


def _extract_policy_period(text: str) -> tuple[str | None, str | None]:
    match = POLICY_PERIOD_PATTERN.search(text)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    return None, None


def _ensure_unique_document_ids(documents: list[DocumentRecord]) -> None:
    adapter = TypeAdapter(list[str])
    document_ids = adapter.validate_python([document.document_id for document in documents])
    duplicates = _duplicates(document_ids)
    if duplicates:
        raise ValueError(f"Duplicate document IDs generated: {', '.join(duplicates)}")


def _ensure_unique_chunk_ids(chunks: list[ChunkRecord]) -> None:
    duplicates = _duplicates([chunk.chunk_id for chunk in chunks])
    if duplicates:
        raise ValueError(f"Duplicate chunk IDs generated: {', '.join(duplicates)}")


def _duplicates(values: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)
