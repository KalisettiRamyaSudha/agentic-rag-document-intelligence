# AGENTS.md

## Project objective
Build a production-oriented Agentic Document Intelligence and Evaluation Platform using FastAPI, LangGraph, BM25, FAISS, cross-encoder reranking, structured citations, and a reproducible evaluation harness.

## Architecture rules
- All retrieval systems must use the same canonical `ChunkRecord` collection.
- Raw text must never be used as a document identity.
- Use stable `document_id` and `chunk_id` values.
- Retrieval components return typed `RetrievalHit` objects.
- Fusion operates on `chunk_id` values using Reciprocal Rank Fusion.
- LangGraph state and API schemas must be typed.
- Deterministic operations must not be replaced with LLM calls.
- The system must abstain when evidence is insufficient.
- Every factual answer must include validated citations.
- Evaluation code must remain separate from production request handling.

## Code quality
- Use Python 3.12.
- Use a `src/` package layout.
- Use Pydantic v2 models.
- Use `pydantic-settings` for configuration.
- Use Ruff for linting and formatting.
- Use Pyright or mypy for type checking.
- Use pytest for tests.
- Do not use `print` in application code.
- Use structured logging.
- Do not catch `Exception` unless re-raising or converting it at an application boundary.
- Do not add dependencies without documenting why they are needed.
- Never commit credentials or sensitive data.

## Testing
Before finishing a task, run:

```bash
make lint
make typecheck
make test
make test-ingestion
```

For API changes:

```bash
make test-api
```

For graph changes:

```bash
make test-agent-paths
```

## LLM testing
- Unit and required CI tests must use fake or stub providers.
- Tests must not require `OPENAI_API_KEY`.
- Do not make network calls in unit tests.
- Keep provider interfaces replaceable.

## Change boundaries
- Keep each task narrowly scoped.
- Avoid unrelated refactoring.
- Preserve backward compatibility unless the task explicitly changes a contract.
- Update tests and documentation when behavior changes.
- Report files changed, design decisions, commands run, and remaining risks.
