"""Persistence for canonical document and chunk stores."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from document_intelligence.models import ChunkRecord, DocumentRecord


def write_documents_jsonl(path: str | Path, documents: list[DocumentRecord]) -> None:
    """Write canonical documents to newline-delimited JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        for document in documents:
            file.write(json.dumps(document.model_dump(), sort_keys=True) + "\n")


def write_chunks_jsonl(path: str | Path, chunks: list[ChunkRecord]) -> None:
    """Write canonical chunks to newline-delimited JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.model_dump(), sort_keys=True) + "\n")


def write_manifest(
    path: str | Path,
    documents: list[DocumentRecord],
    chunks: list[ChunkRecord],
) -> None:
    """Write a collection-level manifest for reproducibility and count checks."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "documents": [
            {
                "document_id": document.document_id,
                "source_uri": document.source_uri,
                "version": document.version,
                "content_checksum": document.content_checksum,
                "chunk_count": sum(
                    1 for chunk in chunks if chunk.document_id == document.document_id
                ),
            }
            for document in documents
        ],
    }
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_sqlite(
    path: str | Path,
    documents: list[DocumentRecord],
    chunks: list[ChunkRecord],
) -> None:
    """Persist canonical records to SQLite without deleting unrelated documents."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _create_schema(connection)
        _upsert_documents(connection, documents)
        for document in documents:
            connection.execute("DELETE FROM chunks WHERE document_id = ?", (document.document_id,))
        _insert_chunks(connection, chunks)


def _upsert_documents(connection: sqlite3.Connection, documents: list[DocumentRecord]) -> None:
    connection.executemany(
        """
        INSERT INTO documents (
            document_id,
            title,
            policy_type,
            version,
            source_uri,
            effective_date,
            expiration_date,
            text,
            content_checksum
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            title = excluded.title,
            policy_type = excluded.policy_type,
            version = excluded.version,
            source_uri = excluded.source_uri,
            effective_date = excluded.effective_date,
            expiration_date = excluded.expiration_date,
            text = excluded.text,
            content_checksum = excluded.content_checksum
        """,
        [
            (
                document.document_id,
                document.title,
                document.policy_type,
                document.version,
                document.source_uri,
                document.effective_date,
                document.expiration_date,
                document.text,
                document.content_checksum,
            )
            for document in documents
        ],
    )


def _insert_chunks(connection: sqlite3.Connection, chunks: list[ChunkRecord]) -> None:
    connection.executemany(
        """
        INSERT INTO chunks (
            chunk_id,
            document_id,
            chunk_index,
            subchunk_ordinal,
            token_count,
            text,
            content_checksum,
            title,
            source_uri,
            policy_type,
            section_key,
            section_number,
            section_title,
            version,
            effective_date,
            expiration_date,
            start_line,
            end_line
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                chunk.chunk_id,
                chunk.document_id,
                chunk.chunk_index,
                chunk.subchunk_ordinal,
                chunk.token_count,
                chunk.text,
                chunk.content_checksum,
                chunk.metadata.title,
                chunk.metadata.source_uri,
                chunk.metadata.policy_type,
                chunk.metadata.section_key,
                chunk.metadata.section_number,
                chunk.metadata.section_title,
                chunk.metadata.version,
                chunk.metadata.effective_date,
                chunk.metadata.expiration_date,
                chunk.metadata.start_line,
                chunk.metadata.end_line,
            )
            for chunk in chunks
        ],
    )


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            version TEXT NOT NULL,
            source_uri TEXT NOT NULL,
            effective_date TEXT,
            expiration_date TEXT,
            text TEXT NOT NULL,
            content_checksum TEXT NOT NULL,
            UNIQUE(source_uri, version)
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            subchunk_ordinal INTEGER NOT NULL,
            token_count INTEGER NOT NULL,
            text TEXT NOT NULL,
            content_checksum TEXT NOT NULL,
            title TEXT NOT NULL,
            source_uri TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            section_key TEXT NOT NULL,
            section_number INTEGER,
            section_title TEXT NOT NULL,
            version TEXT NOT NULL,
            effective_date TEXT,
            expiration_date TEXT,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(document_id),
            UNIQUE(document_id, chunk_index),
            UNIQUE(document_id, section_key, subchunk_ordinal)
        )
        """
    )
