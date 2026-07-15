"""Persistence for canonical document and chunk stores."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Iterable

from rag_document_intelligence.models import ChunkRecord, DocumentRecord


def write_jsonl(path: str | Path, chunks: Iterable[ChunkRecord]) -> None:
    """Write canonical chunks to newline-delimited JSON."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(json.dumps(chunk.to_dict(), sort_keys=True) + "\n")


def write_sqlite(path: str | Path, document: DocumentRecord, chunks: list[ChunkRecord]) -> None:
    """Persist canonical records to SQLite with duplicate protection."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        _create_schema(connection)
        connection.execute("DELETE FROM chunks")
        connection.execute("DELETE FROM documents")
        connection.execute(
            """
            INSERT INTO documents (document_id, source_path, text, metadata_json)
            VALUES (?, ?, ?, ?)
            """,
            (
                document.document_id,
                document.source_path,
                document.text,
                json.dumps(document.metadata, sort_keys=True),
            ),
        )
        connection.executemany(
            """
            INSERT INTO chunks (
                chunk_id,
                document_id,
                chunk_index,
                text,
                source_path,
                section_number,
                section_title,
                start_line,
                end_line
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk.chunk_id,
                    chunk.document_id,
                    chunk.chunk_index,
                    chunk.text,
                    chunk.metadata.source_path,
                    chunk.metadata.section_number,
                    chunk.metadata.section_title,
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
            source_path TEXT NOT NULL,
            text TEXT NOT NULL,
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
            source_path TEXT NOT NULL,
            section_number INTEGER NOT NULL,
            section_title TEXT NOT NULL,
            start_line INTEGER NOT NULL,
            end_line INTEGER NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(document_id),
            UNIQUE(document_id, chunk_index)
        )
        """
    )
