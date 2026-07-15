"""Build the canonical SQLite and JSONL chunk store from the demo dataset."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from rag_document_intelligence.ingestion.canonical import ingest_documents
from rag_document_intelligence.ingestion.store import write_jsonl, write_sqlite


def build_store(source: Path, sqlite_path: Path, jsonl_path: Path) -> None:
    document, chunks = ingest_documents(source)
    write_sqlite(sqlite_path, document, chunks)
    write_jsonl(jsonl_path, chunks)
    print(f"Canonical document ID: {document.document_id}")
    print(f"Canonical chunks written: {len(chunks)}")
    print(f"SQLite store: {sqlite_path}")
    print(f"JSONL store: {jsonl_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=PROJECT_ROOT / "data" / "documents.txt")
    parser.add_argument("--sqlite", type=Path, default=PROJECT_ROOT / "canonical_store" / "chunks.sqlite")
    parser.add_argument("--jsonl", type=Path, default=PROJECT_ROOT / "canonical_store" / "chunks.jsonl")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build_store(args.source, args.sqlite, args.jsonl)


if __name__ == "__main__":
    main()
