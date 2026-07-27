from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest
from pydantic import ValidationError

from document_intelligence.ids import content_checksum, normalize_source_uri
from document_intelligence.ingestion.canonical import (
    EmptyDocumentError,
    ingest_collection,
    ingest_document,
)
from document_intelligence.ingestion.store import (
    write_chunks_jsonl,
    write_documents_jsonl,
    write_manifest,
    write_sqlite,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = PROJECT_ROOT / "data" / "documents.txt"
POLICY_MANIFEST = PROJECT_ROOT / "data" / "policy_manifest.json"
EXPECTED_POLICY_TYPES = {
    "policies/homeowners-ho-2025-0041827.txt": "homeowners",
    "policies/commercial-auto-ca-2025-0098234.txt": "commercial_auto",
    "policies/general-liability-gl-2025-0076543.txt": "general_liability",
    "policies/workers-compensation-wc-2025-0054321.txt": "workers_compensation",
    "policies/umbrella-ub-2025-0032198.txt": "umbrella",
    "policies/professional-liability-pl-2025-0087654.txt": "professional_liability",
    "policies/business-owners-bop-2025-0045678.txt": "business_owners",
    "policies/cyber-liability-cy-2025-0023456.txt": "cyber_liability",
    "policies/inland-marine-im-2025-0011234.txt": "inland_marine",
}


def test_imports_only_document_intelligence() -> None:
    import importlib.util

    assert importlib.util.find_spec("document_intelligence") is not None
    assert importlib.util.find_spec("rag_document_intelligence") is None


def test_source_uri_and_ids_are_path_stable() -> None:
    relative_uri = normalize_source_uri("data/documents.txt", PROJECT_ROOT)
    absolute_uri = normalize_source_uri(DATASET, PROJECT_ROOT)
    assert relative_uri == absolute_uri == "data/documents.txt"

    relative_document, relative_chunks = ingest_document(
        "data/documents.txt", source_root=PROJECT_ROOT, max_tokens=1_000
    )
    absolute_document, absolute_chunks = ingest_document(
        DATASET, source_root=PROJECT_ROOT, max_tokens=1_000
    )
    assert relative_document.document_id == absolute_document.document_id
    assert [chunk.chunk_id for chunk in relative_chunks] == [
        chunk.chunk_id for chunk in absolute_chunks
    ]


def test_manifest_ingests_multiple_policy_documents() -> None:
    documents, chunks = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    assert len(documents) == len(EXPECTED_POLICY_TYPES)
    assert {document.source_uri for document in documents} == set(EXPECTED_POLICY_TYPES)
    document_ids = {document.document_id for document in documents}
    assert all(chunk.document_id in document_ids for chunk in chunks)


def test_policy_type_propagates_from_manifest_to_every_chunk() -> None:
    documents, chunks = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    policy_by_document_id = {document.document_id: document.policy_type for document in documents}
    policy_by_source = {document.source_uri: document.policy_type for document in documents}
    assert policy_by_source == EXPECTED_POLICY_TYPES
    for chunk in chunks:
        assert chunk.metadata.policy_type == policy_by_document_id[chunk.document_id]


def test_commercial_auto_coverage_is_not_classified_as_homeowners() -> None:
    _, chunks = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    commercial_auto_chunks = [
        chunk for chunk in chunks if chunk.metadata.policy_type == "commercial_auto"
    ]
    assert commercial_auto_chunks
    assert any(
        "LIABILITY COVERAGE" in chunk.metadata.section_title for chunk in commercial_auto_chunks
    )
    assert {chunk.metadata.policy_type for chunk in commercial_auto_chunks} == {"commercial_auto"}


def test_document_and_chunk_checksums_are_deterministic() -> None:
    first_documents, first_chunks = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    second_documents, second_chunks = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    assert [document.content_checksum for document in first_documents] == [
        document.content_checksum for document in second_documents
    ]
    assert [chunk.content_checksum for chunk in first_chunks] == [
        chunk.content_checksum for chunk in second_chunks
    ]
    assert first_documents[0].content_checksum == content_checksum(first_documents[0].text)
    assert first_chunks[0].content_checksum == content_checksum(first_chunks[0].text)


def test_empty_documents_are_rejected(tmp_path: Path) -> None:
    empty_file = tmp_path / "empty.txt"
    empty_file.write_text(" \n\t\n", encoding="utf-8")
    with pytest.raises(EmptyDocumentError):
        ingest_document(empty_file, source_root=tmp_path)


def test_preamble_content_is_preserved(tmp_path: Path) -> None:
    policy = tmp_path / "preamble-policy.txt"
    policy.write_text(
        "Important preamble\nBefore sections\n\nSECTION 1: DECLARATIONS\nPolicy body",
        encoding="utf-8",
    )
    _, chunks = ingest_document(policy, source_root=tmp_path, max_tokens=1_000)
    assert chunks[0].metadata.section_key == "PREAMBLE"
    assert "Important preamble" in chunks[0].text


def test_oversized_sections_are_split_into_bounded_subchunks(tmp_path: Path) -> None:
    policy = tmp_path / "large-policy.txt"
    body = " ".join(f"token{i}" for i in range(25))
    policy.write_text(f"SECTION 1: LARGE SECTION\n{body}", encoding="utf-8")
    _, chunks = ingest_document(policy, source_root=tmp_path, max_tokens=10)
    assert len(chunks) == 3
    assert all(chunk.token_count <= 10 for chunk in chunks)
    assert [chunk.subchunk_ordinal for chunk in chunks] == [0, 1, 2]


def test_no_duplicate_document_or_chunk_ids() -> None:
    documents, chunks = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    document_ids = [document.document_id for document in documents]
    chunk_ids = [chunk.chunk_id for chunk in chunks]
    assert len(document_ids) == len(set(document_ids))
    assert len(chunk_ids) == len(set(chunk_ids))


def test_persistence_counts_agree_across_sqlite_jsonl_and_manifest(tmp_path: Path) -> None:
    documents, chunks = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    sqlite_path = tmp_path / "chunks.sqlite"
    documents_jsonl = tmp_path / "documents.jsonl"
    chunks_jsonl = tmp_path / "chunks.jsonl"
    manifest_path = tmp_path / "manifest.json"
    write_sqlite(sqlite_path, documents, chunks)
    write_documents_jsonl(documents_jsonl, documents)
    write_chunks_jsonl(chunks_jsonl, chunks)
    write_manifest(manifest_path, documents, chunks)

    with sqlite3.connect(sqlite_path) as connection:
        sqlite_document_count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        sqlite_chunk_count = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        orphan_count = connection.execute(
            """
            SELECT COUNT(*)
            FROM chunks c
            LEFT JOIN documents d ON c.document_id = d.document_id
            WHERE d.document_id IS NULL
            """
        ).fetchone()[0]
        duplicate_chunk_count = connection.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT chunk_id FROM chunks GROUP BY chunk_id HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0]

    document_rows = documents_jsonl.read_text(encoding="utf-8").splitlines()
    chunk_rows = chunks_jsonl.read_text(encoding="utf-8").splitlines()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert sqlite_document_count == len(document_rows) == manifest["document_count"]
    assert sqlite_chunk_count == len(chunk_rows) == manifest["chunk_count"]
    assert orphan_count == 0
    assert duplicate_chunk_count == 0


def test_updating_one_document_preserves_unrelated_documents(tmp_path: Path) -> None:
    documents, chunks = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    sqlite_path = tmp_path / "chunks.sqlite"
    write_sqlite(sqlite_path, documents, chunks)
    updated_chunks = [chunk for chunk in chunks if chunk.document_id == documents[0].document_id]
    write_sqlite(sqlite_path, [documents[0]], updated_chunks)

    with sqlite3.connect(sqlite_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == len(documents)
        assert connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == len(chunks)


def test_multiple_versions_can_coexist(tmp_path: Path) -> None:
    first_document, first_chunks = ingest_document(DATASET, source_root=PROJECT_ROOT, version="v1")
    second_document, second_chunks = ingest_document(
        DATASET, source_root=PROJECT_ROOT, version="v2"
    )
    sqlite_path = tmp_path / "chunks.sqlite"
    write_sqlite(sqlite_path, [first_document], first_chunks)
    write_sqlite(sqlite_path, [second_document], second_chunks)

    with sqlite3.connect(sqlite_path) as connection:
        versions = {
            row[0] for row in connection.execute("SELECT version FROM documents ORDER BY version")
        }
    assert versions == {"v1", "v2"}


def test_model_records_are_immutable() -> None:
    documents, _ = ingest_collection(POLICY_MANIFEST, source_root=PROJECT_ROOT)
    with pytest.raises(ValidationError, match="frozen"):
        documents[0].document_id = "mutated"
