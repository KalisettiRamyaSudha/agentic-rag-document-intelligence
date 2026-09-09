"""Typed canonical document, chunk, and ingestion collection models."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, model_validator


class DocumentRecord(BaseModel):
    """A logical source document tracked by stable identity and metadata."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    title: str
    policy_type: str
    version: str
    source_uri: str
    effective_date: str | None
    expiration_date: str | None
    text: str
    content_checksum: str


class ChunkMetadata(BaseModel):
    """Queryable traceability metadata inherited from the parent document."""

    model_config = ConfigDict(frozen=True)

    title: str
    source_uri: str
    policy_type: str
    version: str
    effective_date: str | None
    expiration_date: str | None
    section_key: str
    section_number: int | None
    section_title: str
    start_line: int
    end_line: int


class ChunkRecord(BaseModel):
    """Canonical retrieval unit shared by future sparse and dense indexes."""

    model_config = ConfigDict(frozen=True)

    chunk_id: str
    document_id: str
    text: str
    chunk_index: int
    subchunk_ordinal: int
    token_count: int
    content_checksum: str
    metadata: ChunkMetadata


class ManifestDocument(BaseModel):
    """Logical document boundary inside a combined source file."""

    model_config = ConfigDict(frozen=True)

    title: str
    policy_type: str
    source_uri: str
    start_section: PositiveInt
    end_section: PositiveInt
    effective_date: str | None = None
    expiration_date: str | None = None

    @model_validator(mode="after")
    def validate_section_range(self) -> ManifestDocument:
        if self.end_section < self.start_section:
            raise ValueError("end_section must be greater than or equal to start_section")
        return self


class IngestionManifest(BaseModel):
    """Collection-level manifest for splitting combined source files."""

    model_config = ConfigDict(frozen=True)

    collection_id: str
    source_file: Path
    version: str = "v1"
    documents: list[ManifestDocument] = Field(min_length=1)
