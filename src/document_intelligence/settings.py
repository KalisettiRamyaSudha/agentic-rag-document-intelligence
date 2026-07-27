"""Application settings for deterministic local tooling."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Filesystem settings for canonical ingestion artifacts."""

    model_config = SettingsConfigDict(env_prefix="DOC_INTEL_", extra="ignore")

    project_root: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[2])
    canonical_store_dir: Path = Path("canonical_store")
    ingestion_source: Path = Path("data/policy_manifest.json")
    document_version: str = "v1"
    max_chunk_tokens: int = 220

    @property
    def resolved_ingestion_source(self) -> Path:
        return self.project_root / self.ingestion_source

    @property
    def sqlite_path(self) -> Path:
        return self.project_root / self.canonical_store_dir / "chunks.sqlite"

    @property
    def documents_jsonl_path(self) -> Path:
        return self.project_root / self.canonical_store_dir / "documents.jsonl"

    @property
    def chunks_jsonl_path(self) -> Path:
        return self.project_root / self.canonical_store_dir / "chunks.jsonl"

    @property
    def manifest_path(self) -> Path:
        return self.project_root / self.canonical_store_dir / "manifest.json"
