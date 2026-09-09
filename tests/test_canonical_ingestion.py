from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
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


def test_relative_source_resolution_is_independent_of_cwd(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    absolute_document, absolute_chunks = ingest_document(
        DATASET, source_root=PROJECT_ROOT, max_tokens=1_000
    )
    monkeypatch.chdir(tmp_path)

    relative_document, relative_chunks = ingest_document(
        "data/documents.txt", source_root=PROJECT_ROOT, max_tokens=1_000
    )

    assert relative_document.source_uri == "data/documents.txt"
    assert relative_document.version == "v1"
    assert relative_document.document_id == absolute_document.document_id
    assert [chunk.chunk_id for chunk in relative_chunks] == [
        chunk.chunk_id for chunk in absolute_chunks
    ]


def test_manifest_declared_version_is_used_by_default(tmp_path: Path) -> None:
    manifest_data = json.loads(POLICY_MANIFEST.read_text(encoding="utf-8"))
    manifest_data["source_file"] = str(DATASET)
    manifest_data["version"] = "v7"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    documents, chunks = ingest_collection(manifest_path, source_root=PROJECT_ROOT)

    assert {document.version for document in documents} == {"v7"}
    assert {chunk.metadata.version for chunk in chunks} == {"v7"}


def test_explicit_version_override_wins_and_changes_document_ids(tmp_path: Path) -> None:
    manifest_data = json.loads(POLICY_MANIFEST.read_text(encoding="utf-8"))
    manifest_data["source_file"] = str(DATASET)
    manifest_data["version"] = "v7"
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    manifest_documents, _ = ingest_collection(manifest_path, source_root=PROJECT_ROOT)
    override_documents, override_chunks = ingest_collection(
        manifest_path, source_root=PROJECT_ROOT, version="v8"
    )

    assert {document.version for document in override_documents} == {"v8"}
    assert {chunk.metadata.version for chunk in override_chunks} == {"v8"}
    assert all(
        manifest_document.source_uri == override_document.source_uri
        and manifest_document.document_id != override_document.document_id
        for manifest_document, override_document in zip(
            manifest_documents, override_documents, strict=True
        )
    )


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
    source_root = tmp_path / "sources"
    source_root.mkdir()
    source_a = source_root / "policy-a.txt"
    source_b = source_root / "policy-b.txt"
    source_a.write_text(
        "SECTION 1: POLICY A\n" + " ".join(f"original{i}" for i in range(24)),
        encoding="utf-8",
    )
    source_b.write_text("SECTION 1: POLICY B\nUnrelated stable content", encoding="utf-8")
    document_a, chunks_a = ingest_document(source_a, source_root=source_root, max_tokens=10)
    document_b, chunks_b = ingest_document(source_b, source_root=source_root, max_tokens=10)
    assert len(chunks_a) > 1

    sqlite_path = tmp_path / "chunks.sqlite"
    write_sqlite(sqlite_path, [document_a, document_b], [*chunks_a, *chunks_b])
    stale_chunk_ids = {chunk.chunk_id for chunk in chunks_a}

    source_a.write_text("SECTION 1: POLICY A\nUpdated short content", encoding="utf-8")
    updated_document_a, updated_chunks_a = ingest_document(
        source_a, source_root=source_root, max_tokens=10
    )
    assert updated_document_a.document_id == document_a.document_id
    assert len(updated_chunks_a) < len(chunks_a)
    write_sqlite(sqlite_path, [updated_document_a], updated_chunks_a)

    with sqlite3.connect(sqlite_path) as connection:
        assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == len(
            updated_chunks_a
        ) + len(chunks_b)
        stored_b = connection.execute(
            "SELECT text, content_checksum FROM documents WHERE document_id = ?",
            (document_b.document_id,),
        ).fetchone()
        assert stored_b == (document_b.text, document_b.content_checksum)
        stored_b_chunks = connection.execute(
            "SELECT chunk_id, text FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_b.document_id,),
        ).fetchall()
        assert stored_b_chunks == [(chunk.chunk_id, chunk.text) for chunk in chunks_b]
        stored_a_chunks = connection.execute(
            "SELECT chunk_id, text FROM chunks WHERE document_id = ? ORDER BY chunk_index",
            (document_a.document_id,),
        ).fetchall()
        assert stored_a_chunks == [(chunk.chunk_id, chunk.text) for chunk in updated_chunks_a]
        removed_chunk_ids = stale_chunk_ids - {chunk.chunk_id for chunk in updated_chunks_a}
        assert removed_chunk_ids
        for chunk_id in removed_chunk_ids:
            assert (
                connection.execute(
                    "SELECT 1 FROM chunks WHERE chunk_id = ?", (chunk_id,)
                ).fetchone()
                is None
            )
        orphan_count = connection.execute(
            """
            SELECT COUNT(*) FROM chunks c
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
        assert orphan_count == 0
        assert duplicate_count == 0


def test_cli_builds_consistent_store_without_openai_key(tmp_path: Path) -> None:
    sqlite_path = tmp_path / "chunks.sqlite"
    documents_jsonl = tmp_path / "documents.jsonl"
    chunks_jsonl = tmp_path / "chunks.jsonl"
    manifest_path = tmp_path / "manifest.json"
    environment = os.environ.copy()
    environment.pop("OPENAI_API_KEY", None)

    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "build_canonical_store.py"),
            "--source",
            str(POLICY_MANIFEST),
            "--sqlite",
            str(sqlite_path),
            "--documents-jsonl",
            str(documents_jsonl),
            "--chunks-jsonl",
            str(chunks_jsonl),
            "--manifest",
            str(manifest_path),
        ],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert all(
        path.is_file() for path in (sqlite_path, documents_jsonl, chunks_jsonl, manifest_path)
    )
    with sqlite3.connect(sqlite_path) as connection:
        sqlite_document_count = connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
        sqlite_chunk_count = connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    document_jsonl_count = len(documents_jsonl.read_text(encoding="utf-8").splitlines())
    chunk_jsonl_count = len(chunks_jsonl.read_text(encoding="utf-8").splitlines())
    assert sqlite_document_count == document_jsonl_count == manifest["document_count"] == 9
    assert sqlite_chunk_count == chunk_jsonl_count == manifest["chunk_count"]
    assert sqlite_chunk_count > 0


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
