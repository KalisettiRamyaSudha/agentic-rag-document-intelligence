.PHONY: lint typecheck test test-ingestion

lint:
	python -m ruff check src scripts tests

typecheck:
	python -m mypy src scripts tests

test:
	python -m pytest tests

test-ingestion:
	python -m pytest tests/test_canonical_ingestion.py
