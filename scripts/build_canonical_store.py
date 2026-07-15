"""Build the canonical SQLite and JSONL chunk store from the demo dataset."""

# ruff: noqa: E402,I001

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from document_intelligence.ingestion.canonical import ingest_documents
from document_intelligence.ingestion.store import write_jsonl, write_manifest, write_sqlite
from document_intelligence.logging import configure_logging
from document_intelligence.settings import Settings

LOGGER = logging.getLogger(__name__)


def build_store(
    source: Path,
    sqlite_path: Path,
    jsonl_path: Path,
    manifest_path: Path,
    *,
    project_root: Path,
    version: str,
) -> None:
    document, chunks = ingest_documents(source, source_root=project_root, version=version)
    write_sqlite(sqlite_path, document, chunks)
    write_jsonl(jsonl_path, chunks)
    write_manifest(manifest_path, document, chunks)
    LOGGER.info(
        "canonical_store_built",
        extra={
            "event": {
                "document_id": document.document_id,
                "chunk_count": len(chunks),
                "sqlite_store": str(sqlite_path),
                "jsonl_store": str(jsonl_path),
                "manifest": str(manifest_path),
            }
        },
    )


def parse_args(settings: Settings) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=settings.resolved_dataset_path)
    parser.add_argument("--sqlite", type=Path, default=settings.sqlite_path)
    parser.add_argument("--jsonl", type=Path, default=settings.jsonl_path)
    parser.add_argument("--manifest", type=Path, default=settings.manifest_path)
    parser.add_argument("--version", default=settings.document_version)
    return parser.parse_args()


def main() -> None:
    configure_logging()
    settings = Settings(project_root=PROJECT_ROOT)
    args = parse_args(settings)
    build_store(
        args.source,
        args.sqlite,
        args.jsonl,
        args.manifest,
        project_root=settings.project_root,
        version=args.version,
    )


if __name__ == "__main__":
    main()
