# Agentic RAG Document Intelligence

This repository is a work-in-progress insurance document intelligence demo. The current migration focus is **canonical ingestion**: deterministic document/chunk records with stable identifiers, checksums, metadata, SQLite persistence, JSONL exports, and tests.

The application is **not production-ready**. Hybrid retrieval, Reciprocal Rank Fusion, typed LangGraph orchestration, citation validation, Docker, and deployment are documented in the roadmap but are not implemented in this migration step.

## Current architecture status

Implemented:
- `src/document_intelligence` package layout
- Pydantic v2 `DocumentRecord`, `ChunkRecord`, and `ChunkMetadata` models
- Stable document/chunk identifiers and content checksums
- Manifest-driven ingestion of multiple logical policy documents from `data/documents.txt`
- Section-aware chunking with preamble preservation and bounded deterministic
  whitespace-token subchunking (not a model tokenizer)
- SQLite persistence plus `documents.jsonl`, `chunks.jsonl`, and `manifest.json`
- Ruff, mypy, pytest, Makefile commands, and GitHub Actions CI

Legacy demo files are still present at the repository root (`ingest.py`, `hybrid_retriever.py`, `agent.py`, `app.py`, and related scripts). They are preserved for compatibility and will be migrated in later phases.

## Repository

```bash
git clone https://github.com/KalisettiRamyaSudha/agentic-rag-document-intelligence.git
cd agentic-rag-document-intelligence
```

## Setup

Use Python 3.12 or newer.

```bash
python -m pip install -e '.[dev]'
```

## Build the canonical store

```bash
python scripts/build_canonical_store.py
```

By default this writes generated artifacts under `canonical_store/`:

- `chunks.sqlite`
- `documents.jsonl`
- `chunks.jsonl`
- `manifest.json`

Generated canonical-store artifacts are ignored by Git.

SQLite writes support partial, non-destructive document updates: replacing a supplied
document also replaces that document's chunks while preserving unrelated documents.
`documents.jsonl` and `chunks.jsonl` are complete snapshots of the collection supplied
to their writers rather than partial-update stores.

## Checks

```bash
make lint
make typecheck
make test
make test-ingestion
```

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the planned phases.

Near-term completed/focused phases:
1. Project foundation
2. Canonical ingestion and stable identifiers

Later phases:
- Canonical BM25/FAISS retrieval over the same chunks
- Reciprocal Rank Fusion and typed `RetrievalHit`
- Typed LangGraph orchestration
- Citation validation and abstention
- Evaluation harness
- API hardening
- Docker, CI hardening, observability, and deployment

## Known limitations

- Retrieval still uses the legacy proof-of-concept implementation and has not yet been migrated to canonical chunks.
- `make test-ingestion` validates canonical ingestion only; it is not a retrieval quality test.
- LLM answer generation is still demo-oriented and is not part of this canonical ingestion migration.
- The synthetic dataset is fixture data for development and evaluation scaffolding, not real insurance policy data.
- Manifest-driven ingestion does not assign content before the first `SECTION` to a
  logical policy; preamble ownership must be made explicit in a future manifest contract.
