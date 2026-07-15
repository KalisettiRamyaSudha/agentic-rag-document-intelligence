"""Stable identifier generation for canonical documents and chunks."""

from __future__ import annotations

import hashlib


def normalize_text(text: str) -> str:
    """Normalize line endings and trim document-edge whitespace only."""
    return text.replace("\r\n", "\n").replace("\r", "\n").strip()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def make_document_id(source_path: str, text: str) -> str:
    """Create a deterministic content-addressed document ID."""
    normalized = normalize_text(text)
    return f"doc:v1:{_digest(source_path + '\n' + normalized)}"


def make_chunk_id(document_id: str, chunk_index: int, text: str) -> str:
    """Create a deterministic chunk ID scoped to a parent document."""
    normalized = normalize_text(text)
    seed = f"{document_id}\n{chunk_index}\n{normalized}"
    return f"chunk:v1:{_digest(seed)}"
