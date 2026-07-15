from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from rag_document_intelligence.ids import make_chunk_id, make_document_id, normalize_text
from rag_document_intelligence.ingestion.canonical import ingest_documents
from rag_document_intelligence.ingestion.store import write_jsonl, write_sqlite

DATASET = PROJECT_ROOT / "data" / "documents.txt"


class CanonicalIngestionTests(unittest.TestCase):
    def test_id_stability(self) -> None:
        text = "A\r\nB\n"
        first_doc_id = make_document_id("demo.txt", text)
        second_doc_id = make_document_id("demo.txt", normalize_text(text))
        self.assertEqual(first_doc_id, second_doc_id)

        first_chunk_id = make_chunk_id(first_doc_id, 0, text)
        second_chunk_id = make_chunk_id(first_doc_id, 0, normalize_text(text))
        self.assertEqual(first_chunk_id, second_chunk_id)

    def test_metadata_preservation_and_chunk_ordering(self) -> None:
        document, chunks = ingest_documents(DATASET)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].metadata.section_number, 1)
        self.assertEqual(chunks[0].metadata.section_title, "HOMEOWNERS POLICY - DECLARATIONS PAGE")
        self.assertEqual(chunks[0].metadata.start_line, 1)
        self.assertEqual(chunks[0].chunk_index, 0)

        for expected_index, chunk in enumerate(chunks):
            self.assertEqual(chunk.document_id, document.document_id)
            self.assertEqual(chunk.chunk_index, expected_index)
            self.assertLessEqual(chunk.metadata.start_line, chunk.metadata.end_line)
            self.assertEqual(chunk.metadata.source_path, DATASET.as_posix())

    def test_duplicate_prevention(self) -> None:
        _, chunks = ingest_documents(DATASET)
        chunk_ids = [chunk.chunk_id for chunk in chunks]
        self.assertEqual(len(chunk_ids), len(set(chunk_ids)))

    def test_repeatable_ingestion(self) -> None:
        first_document, first_chunks = ingest_documents(DATASET)
        second_document, second_chunks = ingest_documents(DATASET)

        self.assertEqual(first_document.document_id, second_document.document_id)
        self.assertEqual(
            [(chunk.chunk_id, chunk.chunk_index, chunk.metadata.section_number) for chunk in first_chunks],
            [(chunk.chunk_id, chunk.chunk_index, chunk.metadata.section_number) for chunk in second_chunks],
        )

    def test_persistence_to_sqlite_and_jsonl(self) -> None:
        document, chunks = ingest_documents(DATASET)
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "chunks.sqlite"
            jsonl_path = Path(temp_dir) / "chunks.jsonl"
            write_sqlite(sqlite_path, document, chunks)
            write_jsonl(jsonl_path, chunks)

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

            self.assertEqual(doc_count, 1)
            self.assertEqual(chunk_count, len(chunks))
            self.assertEqual(orphan_count, 0)
            self.assertEqual(duplicate_count, 0)

            jsonl_rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(jsonl_rows), len(chunks))
            self.assertEqual(jsonl_rows[0]["chunk_id"], chunks[0].chunk_id)
            self.assertEqual(jsonl_rows[0]["metadata"]["section_number"], 1)


if __name__ == "__main__":
    unittest.main()
