"""Build the canonical SQLite and JSONL document/chunk store."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from document_intelligence.ingestion.canonical import ingest_collection
from document_intelligence.ingestion.store import (
    write_chunks_jsonl,
    write_documents_jsonl,
    write_manifest,
    write_sqlite,
)
from document_intelligence.logging import configure_logging
from document_intelligence.settings import Settings

LOGGER = logging.getLogger(__name__)


def build_store(
    source: Path,
    sqlite_path: Path,
    documents_jsonl_path: Path,
    chunks_jsonl_path: Path,
    manifest_path: Path,
    *,
    project_root: Path,
    version: str,
    max_tokens: int,
) -> None:
    documents, chunks = ingest_collection(
        source,
        source_root=project_root,
        version=version,
        max_tokens=max_tokens,
    )
    write_sqlite(sqlite_path, documents, chunks)
    write_documents_jsonl(documents_jsonl_path, documents)
    write_chunks_jsonl(chunks_jsonl_path, chunks)
    write_manifest(manifest_path, documents, chunks)
    LOGGER.info(
        "canonical_store_built",
        extra={
            "event": {
                "document_count": len(documents),
                "chunk_count": len(chunks),
                "sqlite_store": str(sqlite_path),
                "documents_jsonl": str(documents_jsonl_path),
                "chunks_jsonl": str(chunks_jsonl_path),
                "manifest": str(manifest_path),
            }
        },
    )


def parse_args(settings: Settings) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=settings.resolved_ingestion_source)
    parser.add_argument("--sqlite", type=Path, default=settings.sqlite_path)
    parser.add_argument("--documents-jsonl", type=Path, default=settings.documents_jsonl_path)
    parser.add_argument("--chunks-jsonl", type=Path, default=settings.chunks_jsonl_path)
    parser.add_argument("--manifest", type=Path, default=settings.manifest_path)
    parser.add_argument("--version", default=settings.document_version)
    parser.add_argument("--max-tokens", type=int, default=settings.max_chunk_tokens)
    return parser.parse_args()


def main() -> None:
    configure_logging()
    settings = Settings()
    args = parse_args(settings)
    build_store(
        args.source,
        args.sqlite,
        args.documents_jsonl,
        args.chunks_jsonl,
        args.manifest,
        project_root=settings.project_root,
        version=args.version,
        max_tokens=args.max_tokens,
    )


if __name__ == "__main__":
    main()
