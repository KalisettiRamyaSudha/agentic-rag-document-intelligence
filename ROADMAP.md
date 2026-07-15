# Agentic Document Intelligence and Evaluation Platform Roadmap

This roadmap transforms the current proof-of-concept RAG repository into a
production-oriented, portfolio-ready document intelligence platform.

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

## Suggested branch sequence

1. `agent/project-foundation`
2. `agent/canonical-ingestion`
3. `agent/hybrid-retrieval-rrf`
4. `agent/langgraph-workflow`
5. `agent/evaluation-harness`
6. `agent/api-hardening`
7. `agent/docker-ci-observability`
8. `agent/cloud-run-portfolio-demo`

---

## Phase 1 — Project foundation

### Scope

- Introduce `src/document_intelligence/` package layout.
- Add `pyproject.toml` with controlled dependencies.
- Add Pydantic Settings configuration.
- Add typed core domain models.
- Add structured logging.
- Add Ruff, type checking, pytest, Makefile commands, and fixtures.
- Add `AGENTS.md`.
- Preserve current demo behavior.

### Acceptance criteria

- [ ] Application imports from the new package.
- [ ] `make lint`, `make typecheck`, and `make test` pass.
- [ ] Tests require no OpenAI key or network access.
- [ ] No secrets or generated indexes are committed.
- [ ] Existing synthetic data remains available.

### Depends on

Nothing.

---

## Phase 2 — Canonical ingestion and stable identifiers

### Scope

- Create `DocumentRecord`, `ChunkRecord`, and `ChunkMetadata`.
- Parse the existing dataset into section-aware canonical chunks.
- Generate stable `document_id` and `chunk_id` values.
- Store policy type, section, version, source, effective date, and checksum.
- Persist canonical records to SQLite and JSONL.
- Add duplicate detection and ingestion manifests.
- Build migration tooling from `data/documents.txt`.

### Identifier strategy

- `document_id = sha256(normalized_source_uri + version)[:16]`
- `chunk_id = document_id + ":" + zero_padded_ordinal`
- Store a separate content checksum for change detection.

### Acceptance criteria

- [ ] Running ingestion twice produces identical IDs and ordering.
- [ ] Every chunk belongs to a valid document.
- [ ] No duplicate chunk IDs exist.
- [ ] Metadata is preserved and queryable.
- [ ] Ingestion runs without an LLM or network connection.
- [ ] Existing data is not deleted.

### Depends on

Phase 1.

---

## Phase 3 — Canonical hybrid retrieval with RRF

### Scope

- Build BM25 from canonical chunks.
- Build FAISS from the exact same canonical chunks.
- Map all retriever results to `chunk_id`.
- Add metadata filtering.
- Implement Reciprocal Rank Fusion.
- Add cross-encoder reranking.
- Return `RetrievalHit` objects rather than raw strings.
- Remove unsafe/deserialization-dependent canonical storage behavior.
- Record intermediate ranks and scores.

### Acceptance criteria

- [ ] BM25 and FAISS index the same ordered chunk IDs.
- [ ] RRF operates on chunk IDs.
- [ ] Retrieval returns source metadata and short excerpts.
- [ ] Exact identifiers and numeric queries are covered by tests.
- [ ] Version and policy filters exclude incorrect documents.
- [ ] MRR and nDCG are measured before and after reranking.

### Depends on

Phase 2.

---

## Phase 4 — Typed LangGraph workflow

### Nodes

- Query classification
- Query rewriting
- Metadata extraction
- Metadata-filtered retrieval
- Hybrid retrieval
- Reranking
- Context sufficiency
- Answer generation
- Citation validation
- Retry/fallback
- Abstention
- Trace finalization

### Routing behavior

- Out-of-domain queries abstain without retrieval.
- Insufficient context receives at most one controlled retry.
- Invalid citations receive at most one controlled regeneration.
- The graph has a hard maximum step count.
- Deterministic validation does not call an LLM.

### Acceptance criteria

- [ ] Graph state is fully typed.
- [ ] All major graph paths have tests using fake providers.
- [ ] Unsupported questions abstain clearly.
- [ ] Generated factual answers contain valid citation IDs.
- [ ] Invalid citations cannot silently pass.
- [ ] Tool calls and graph paths are captured in a trace.

### Depends on

Phase 3.

---

## Phase 5 — Evaluation dataset and harness

### Dataset target

Create 80 carefully labeled cases:

- 20 single-section answerable
- 10 multi-section reasoning
- 10 multi-document comparison
- 10 exact number or identifier
- 10 metadata/version filtering
- 10 unanswerable
- 5 rewrite-required
- 5 adversarial/citation-stress

### Metrics

Retrieval:

- Recall@k
- Precision@k
- MRR
- nDCG
- Metadata-filter accuracy
- Reranker uplift

Answer:

- Faithfulness
- Answer relevance
- Citation support
- Citation correctness
- Citation completeness
- Numerical consistency
- Abstention correctness

Agent:

- Query-classification accuracy
- Tool-selection accuracy
- Redundant tool calls
- Graph-path correctness
- End-to-end task completion
- Retry frequency

Operations:

- Total latency
- Per-stage latency
- Token usage
- Estimated cost
- Error and timeout rates

### Acceptance criteria

- [ ] Every test case has stable relevant chunk IDs.
- [ ] Evaluation runs are versioned by commit SHA, config hash, dataset version, and model versions.
- [ ] Reports are emitted as JSON and Markdown.
- [ ] CI runs a deterministic smoke subset.
- [ ] Full evaluation is runnable manually.
- [ ] No reported metric relies only on keyword presence.

### Depends on

Phases 3 and 4.

---

## Phase 6 — FastAPI hardening and API tests

### Scope

- Add versioned API routes.
- Add typed request and response schemas.
- Add validation and maximum query limits.
- Add dependency injection and application lifespan handling.
- Add exception handlers.
- Add provider timeouts and rate-limit handling.
- Add liveness and readiness endpoints.
- Add request IDs and trace IDs.
- Protect or disable administrative index routes in public deployments.

### Suggested routes

- `POST /api/v1/query`
- `POST /api/v1/evaluations`
- `GET /api/v1/evaluations/{run_id}`
- `GET /api/v1/documents`
- `GET /health/live`
- `GET /health/ready`

### Acceptance criteria

- [ ] API responses never expose raw internal exceptions.
- [ ] Timeout and rate-limit failures map to documented responses.
- [ ] Readiness fails when required indexes are unavailable.
- [ ] API tests cover success, validation, abstention, timeout, and provider failure.
- [ ] Full raw chunks are not returned as citations.

### Depends on

Phase 4.

---

## Phase 7 — Docker, CI, security, and observability

### Scope

- Add a non-root multi-stage Dockerfile.
- Add Docker health checks.
- Add GitHub Actions for lint, typing, tests, retrieval smoke evaluation, and image build.
- Add dependency/security scanning.
- Add structured JSON logging.
- Add latency, token, cost, error, and graph-path metrics.
- Upload evaluation summaries as workflow artifacts.

### Acceptance criteria

- [ ] Container starts using the injected `PORT`.
- [ ] CI is deterministic and does not require an LLM key.
- [ ] Docker build succeeds on every pull request.
- [ ] Logs include request ID, graph path, timings, outcome, and error class.
- [ ] Secrets never appear in logs or repository history.
- [ ] The service runs as a non-root user.

### Depends on

Phases 5 and 6.

---

## Phase 8 — Deployment and portfolio presentation

### Recommended deployment

- FastAPI backend on Google Cloud Run
- Secret Manager for provider credentials
- Artifact Registry for images
- GitHub Actions deployment from `main`
- Optional Streamlit or lightweight frontend
- Maximum instance cap to control cost

### Portfolio deliverables

- Deployed public demo
- OpenAPI documentation
- Architecture diagram
- Evaluation results table
- BM25 vs dense vs RRF vs reranked comparison
- Correct abstention examples
- Citation-validation examples
- Latency and cost report
- CI badge
- Docker instructions
- Trade-offs and limitations
- Short demo video or screenshots

### Acceptance criteria

- [ ] Public demo is reachable.
- [ ] Administrative actions are protected or disabled.
- [ ] Deployment is reproducible from repository instructions.
- [ ] README reports only measured results.
- [ ] At least one failure-analysis section is included.
- [ ] Repository is described as production-oriented unless full operational evidence supports stronger wording.

### Depends on

Phase 7.

---

## Suggested portfolio quality gates

These are targets and must not be presented as achieved until measured.

| Metric | Target |
|---|---:|
| Recall@5 | >= 0.90 |
| MRR | >= 0.80 |
| nDCG@10 | >= 0.85 |
| Citation support | >= 0.95 |
| Faithfulness | >= 0.90 |
| Abstention correctness | >= 0.90 |
| Tool-selection accuracy | >= 0.95 |
| End-to-end completion | >= 0.85 |
| Redundant tool calls | <= 0.10 per run |

## Definition of done

The transformation is complete when the repository contains:

- Correct canonical retrieval
- Conditional LangGraph orchestration
- Citation validation and abstention
- Reproducible evaluation
- Typed backend contracts
- Meaningful tests
- Docker and CI
- A deployed demo
- Measured results
- Honest limitations and design trade-offs
