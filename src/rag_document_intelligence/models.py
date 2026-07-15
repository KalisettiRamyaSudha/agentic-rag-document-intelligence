"""Typed canonical document and chunk models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    """A normalized source document tracked by a stable identifier."""

    document_id: str
    source_path: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """Traceability metadata for a section-aware canonical chunk."""

    source_path: str
    section_number: int
    section_title: str
    start_line: int
    end_line: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    """Canonical retrieval unit shared by future sparse and dense indexes."""

    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    metadata: ChunkMetadata

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        return data
