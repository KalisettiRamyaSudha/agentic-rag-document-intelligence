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
    dataset_path: Path = Path("data/documents.txt")
    document_version: str = "v1"

    @property
    def resolved_dataset_path(self) -> Path:
        return self.project_root / self.dataset_path

    @property
    def sqlite_path(self) -> Path:
        return self.project_root / self.canonical_store_dir / "chunks.sqlite"

    @property
    def jsonl_path(self) -> Path:
        return self.project_root / self.canonical_store_dir / "chunks.jsonl"

    @property
    def manifest_path(self) -> Path:
        return self.project_root / self.canonical_store_dir / "manifest.json"
