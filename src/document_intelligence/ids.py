"""Stable identifier and checksum generation for canonical records."""

from __future__ import annotations

import hashlib
from pathlib import Path


def normalize_text(text: str) -> str:
    """Normalize line endings and trim document-edge whitespace only."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def normalize_source_uri(source_path: str | Path, source_root: str | Path | None = None) -> str:
    """Return a stable logical source URI for relative or absolute file inputs."""
    path = Path(source_path)
    root = Path.cwd() if source_root is None else Path(source_root)
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def content_checksum(text: str) -> str:
    """Create a full content checksum for change detection."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def make_document_id(source_uri: str, version: str) -> str:
    """Create a deterministic document ID from logical source URI and version."""
    return _digest(f"{source_uri}\n{version}")


def make_chunk_id(document_id: str, section_key: str, subchunk_ordinal: int) -> str:
    """Create a deterministic chunk ID scoped to document, section, and subchunk."""
    return f"{document_id}:{section_key}:{subchunk_ordinal:04d}"
