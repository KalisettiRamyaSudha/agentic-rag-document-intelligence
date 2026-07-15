# Agentic Document Intelligence and Evaluation Platform Roadmap

This roadmap transforms the current proof-of-concept RAG repository into a production-oriented, portfolio-ready document intelligence platform.

## Product objective
Build a deployed platform that demonstrates:
- Canonical document ingestion and stable identifiers
- Metadata-aware BM25 and FAISS retrieval over the same chunks
- Reciprocal Rank Fusion and cross-encoder reranking
- Typed LangGraph orchestration with controlled retries and abstention
- Citation-grounded answer generation and validation
- Reproducible retrieval, answer, agent-path, latency, and cost evaluation
- Production-style FastAPI contracts, logging, exception handling, tests, Docker, CI, and deployment

## Delivery principles
1. Retrieval correctness comes before agent orchestration.
2. BM25 and FAISS must use the same canonical `ChunkRecord` collection.
3. Raw text must never be used as a document identity.
4. Deterministic steps must remain deterministic rather than becoming LLM calls.
5. CI tests must not require external API keys or network access.
6. Every phase should be completed through a focused branch and pull request.
7. Metrics must be measured and stored; do not claim unmeasured quality.

## Phase 1 — Project foundation
- Introduce `src/document_intelligence/` package layout.
- Add `pyproject.toml` with controlled dependencies.
- Add Pydantic Settings configuration.
- Add typed core domain models.
- Add structured logging.
- Add Ruff, type checking, pytest, Makefile commands, GitHub Actions, and fixtures.
- Add `AGENTS.md`.
- Preserve current demo behavior.

## Phase 2 — Canonical ingestion and stable identifiers
- Create `DocumentRecord`, `ChunkRecord`, and `ChunkMetadata`.
- Parse the existing dataset into section-aware canonical chunks.
- Generate stable `document_id` and `chunk_id` values.
- Store policy type, section, version, source, effective date, and checksum.
- Persist canonical records to SQLite and JSONL.
- Add duplicate detection and ingestion manifests.
- Build migration tooling from `data/documents.txt`.

## Later phases
- Phase 3: Canonical hybrid retrieval with BM25, FAISS, Reciprocal Rank Fusion, metadata filtering, and `RetrievalHit` results.
- Phase 4: Typed LangGraph workflow, citation validation, controlled retries, and abstention.
- Phase 5: Reproducible evaluation dataset and harness.
- Phase 6: FastAPI hardening and API tests.
- Phase 7: Docker, CI, security, and observability.
- Phase 8: Deployment and portfolio presentation.
