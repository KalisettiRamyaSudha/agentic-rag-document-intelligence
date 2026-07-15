from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from document_intelligence.ids import make_chunk_id, make_document_id, normalize_source_uri
from document_intelligence.ingestion.canonical import ingest_documents
from document_intelligence.ingestion.store import write_jsonl, write_manifest, write_sqlite

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "data" / "documents.txt"


def test_id_stability() -> None:
    first_doc_id = make_document_id("demo.txt", "v1")
    second_doc_id = make_document_id("demo.txt", "v1")
    assert first_doc_id == second_doc_id

    first_chunk_id = make_chunk_id(first_doc_id, 0)
    second_chunk_id = make_chunk_id(first_doc_id, 0)
    assert first_chunk_id == second_chunk_id


def test_source_uri_normalization_is_path_stable() -> None:
    relative_uri = normalize_source_uri("data/documents.txt", PROJECT_ROOT)
    absolute_uri = normalize_source_uri(DATASET, PROJECT_ROOT)
    assert relative_uri == absolute_uri
    assert relative_uri == "data/documents.txt"


def test_metadata_preservation_and_chunk_ordering() -> None:
    document, chunks = ingest_documents(DATASET, source_root=PROJECT_ROOT)

    assert len(chunks) > 1
    assert chunks[0].metadata.section_number == 1
    assert chunks[0].metadata.section_title == "HOMEOWNERS POLICY - DECLARATIONS PAGE"
    assert chunks[0].metadata.start_line == 1
    assert chunks[0].chunk_index == 0

    for expected_index, chunk in enumerate(chunks):
        assert chunk.document_id == document.document_id
        assert chunk.chunk_index == expected_index
        assert chunk.metadata.start_line <= chunk.metadata.end_line
        assert chunk.metadata.source_uri == "data/documents.txt"
        assert chunk.metadata.version == "v1"
        assert chunk.metadata.content_checksum


def test_duplicate_prevention() -> None:
    _, chunks = ingest_documents(DATASET, source_root=PROJECT_ROOT)
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))


def test_repeatable_ingestion() -> None:
    first_document, first_chunks = ingest_documents(DATASET, source_root=PROJECT_ROOT)
    second_document, second_chunks = ingest_documents(
        "data/documents.txt", source_root=PROJECT_ROOT
    )

    assert first_document.document_id == second_document.document_id
    first_order = [
        (chunk.chunk_id, chunk.chunk_index, chunk.metadata.section_number) for chunk in first_chunks
    ]
    second_order = [
        (chunk.chunk_id, chunk.chunk_index, chunk.metadata.section_number)
        for chunk in second_chunks
    ]
    assert first_order == second_order


def test_persistence_to_sqlite_jsonl_and_manifest(tmp_path: Path) -> None:
    document, chunks = ingest_documents(DATASET, source_root=PROJECT_ROOT)
    sqlite_path = tmp_path / "chunks.sqlite"
    jsonl_path = tmp_path / "chunks.jsonl"
    manifest_path = tmp_path / "manifest.json"
    write_sqlite(sqlite_path, document, chunks)
    write_jsonl(jsonl_path, chunks)
    write_manifest(manifest_path, document, chunks)

    with sqlite3.connect(sqlite_path) as connection:
        doc_count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        chunk_count = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        orphan_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM chunks c
            LEFT JOIN documents d ON c.document_id = d.document_id
            WHERE d.document_id IS NULL
            """
        ).fetchone()[0]
        duplicate_count = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT chunk_id FROM chunks GROUP BY chunk_id HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

    assert doc_count == 1
    assert chunk_count == len(chunks)
    assert orphan_count == 0
    assert duplicate_count == 0

    jsonl_rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert len(jsonl_rows) == len(chunks)
    assert jsonl_rows[0]["chunk_id"] == chunks[0].chunk_id
    assert jsonl_rows[0]["metadata"]["section_number"] == 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["document_id"] == document.document_id
    assert manifest["chunk_ids"] == [chunk.chunk_id for chunk in chunks]


def test_sqlite_writer_preserves_unrelated_documents(tmp_path: Path) -> None:
    document, chunks = ingest_documents(DATASET, source_root=PROJECT_ROOT)
    other_document, other_chunks = ingest_documents(DATASET, source_root=PROJECT_ROOT, version="v2")
    sqlite_path = tmp_path / "chunks.sqlite"
    write_sqlite(sqlite_path, document, chunks)
    write_sqlite(sqlite_path, other_document, other_chunks)

    with sqlite3.connect(sqlite_path) as connection:
        doc_count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        first_doc_chunks = connection.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (document.document_id,)
        ).fetchone()[0]
        second_doc_chunks = connection.execute(
            "SELECT COUNT(*) FROM chunks WHERE document_id = ?", (other_document.document_id,)
        ).fetchone()[0]

    assert doc_count == 2
    assert first_doc_chunks == len(chunks)
    assert second_doc_chunks == len(other_chunks)


def test_model_records_are_immutable() -> None:
    document, _ = ingest_documents(DATASET, source_root=PROJECT_ROOT)
    with pytest.raises(ValidationError, match="frozen"):
        document.document_id = "mutated"
