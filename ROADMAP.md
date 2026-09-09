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
- [x] Introduce `src/document_intelligence/` package layout.
- [x] Add `pyproject.toml` with controlled dependencies.
- [x] Add Pydantic Settings configuration.
- [x] Add typed core domain models.
- [x] Add structured logging.
- [x] Add Ruff, type checking, pytest, Makefile commands, GitHub Actions, and fixtures.
- [x] Add `AGENTS.md`.
- [ ] Preserve and test current demo behavior while later components are migrated.

## Phase 2 — Canonical ingestion and stable identifiers
- [x] Create `DocumentRecord`, `ChunkRecord`, and `ChunkMetadata`.
- [x] Parse the existing dataset into section-aware canonical chunks.
- [x] Generate stable `document_id` and `chunk_id` values.
- [x] Store policy type, section, version, source, effective date, and checksum.
- [x] Persist canonical records to SQLite and JSONL.
- [x] Add duplicate detection and ingestion manifests.
- [x] Build migration tooling from `data/documents.txt`.
- [x] Verify manifest version precedence and explicit overrides.
- [x] Verify source identity is independent of the process working directory.
- [x] Verify partial SQLite updates replace stale chunks and preserve unrelated documents.
- [x] Verify the CLI builds consistent artifacts without an LLM API key.

## Later phases
- Phase 3: Canonical hybrid retrieval with BM25, FAISS, Reciprocal Rank Fusion, metadata filtering, and `RetrievalHit` results.
- Phase 4: Typed LangGraph workflow, citation validation, controlled retries, and abstention.
- Phase 5: Reproducible evaluation dataset and harness.
- Phase 6: FastAPI hardening and API tests.
- Phase 7: Docker, CI, security, and observability.
- Phase 8: Deployment and portfolio presentation.
