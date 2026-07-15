"""Persistence for canonical document and chunk stores."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path

from document_intelligence.models import ChunkRecord, DocumentRecord


def write_jsonl(path: str | Path, chunks: Iterable[ChunkRecord]) -> None:
    """Write canonical chunks to newline-delimited JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.model_dump(), sort_keys=True) + "\n")


def write_manifest(path: str | Path, document: DocumentRecord, chunks: list[ChunkRecord]) -> None:
    """Write an ingestion manifest for reproducibility and change detection."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "document_id": document.document_id,
        "source_uri": document.source_uri,
        "version": document.version,
        "content_checksum": document.content_checksum,
        "chunk_count": len(chunks),
        "chunk_ids": [chunk.chunk_id for chunk in chunks],
    }
    target.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_sqlite(path: str | Path, document: DocumentRecord, chunks: list[ChunkRecord]) -> None:
    """Persist canonical records to SQLite without deleting unrelated documents."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _create_schema(connection)
        connection.execute(
            """
            INSERT INTO documents (
                document_id,
                source_uri,
                version,
                text,
                content_checksum,
                metadata_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(document_id) DO UPDATE SET
                source_uri = excluded.source_uri,
                version = excluded.version,
                text = excluded.text,
                content_checksum = excluded.content_checksum,
                metadata_json = excluded.metadata_json
            """,
            (
                document.document_id,
                document.source_uri,
                document.version,
                document.text,
                document.content_checksum,
                json.dumps(document.metadata, sort_keys=True),
            ),
        )
        connection.execute("DELETE FROM chunks WHERE document_id = ?", (document.document_id,))
        connection.executemany(
            """
            INSERT INTO chunks (
                chunk_id,
                document_id,
                chunk_index,
                text,
                source_uri,
                policy_type,
                section_number,
                section_title,
                version,
                effective_date,
                start_line,
                end_line,
                content_checksum
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk.chunk_id,
                    chunk.document_id,
                    chunk.chunk_index,
                    chunk.text,
                    chunk.metadata.source_uri,
                    chunk.metadata.policy_type,
                    chunk.metadata.section_number,
                    chunk.metadata.section_title,
                    chunk.metadata.version,
                    chunk.metadata.effective_date,
                    chunk.metadata.start_line,
                    chunk.metadata.end_line,
                    chunk.metadata.content_checksum,
                )
                for chunk in chunks
            ],
        )


def _create_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            source_uri TEXT NOT NULL,
            version TEXT NOT NULL,
            text TEXT NOT NULL,
            content_checksum TEXT NOT NULL,
            metadata_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS chunks (
            chunk_id TEXT PRIMARY KEY,
            document_id TEXT NOT NULL,
            chunk_index INTEGER NOT NULL,
            text TEXT NOT NULL,
            source_uri TEXT NOT NULL,
            policy_type TEXT NOT NULL,
            section_number INTEGER NOT NULL,
            section_title TEXT NOT NULL,
            version TEXT NOT NULL,
            effective_date TEXT,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            content_checksum TEXT NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(document_id),
            UNIQUE(document_id, chunk_index)
        )
        """
    )
