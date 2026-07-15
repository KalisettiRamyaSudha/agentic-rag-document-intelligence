"""Typed canonical document and chunk models."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class DocumentRecord(BaseModel):
    """A normalized source document tracked by a stable logical identifier."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    source_uri: str
    version: str
    text: str
    content_checksum: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChunkMetadata(BaseModel):
    """Queryable traceability metadata for a section-aware canonical chunk."""

    model_config = ConfigDict(frozen=True)

    source_uri: str
    policy_type: str
    section_number: int
    section_title: str
    version: str
    effective_date: str | None
    start_line: int
    end_line: int
    content_checksum: str


class ChunkRecord(BaseModel):
    """Canonical retrieval unit shared by future sparse and dense indexes."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    metadata: ChunkMetadata
