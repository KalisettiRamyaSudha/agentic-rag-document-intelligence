# Insurance Policy RAG System

An **Agentic Retrieval-Augmented Generation (RAG)** system built for P&C insurance policy document intelligence. Combines hybrid retrieval, cross-encoder reranking, and LLM reasoning to answer questions over insurance policy collections.

## Architecture

```
User Query
    │
    ▼
┌─────────────────────────┐
│   Hybrid Retriever      │
│  (BM25 + FAISS Dense)   │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Cross-Encoder Reranker │
│  (ms-marco-MiniLM-L6)   │
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│   LLM Answer Generation │
│   (OpenAI GPT-3.5)      │
└──────────┬──────────────┘
           │
           ▼
   Structured Response
   (Answer + Sources)
```

## Why Hybrid Retrieval?

Insurance documents contain both **specific identifiers** (policy numbers, coverage codes, dollar amounts) and **conceptual language** (exclusions, endorsements, liability terms). A single retrieval strategy fails:

- **BM25 alone** misses semantic similarity — "What's not covered?" won't match "exclusions"
- **Dense vectors alone** miss exact terms — policy numbers and coverage limits need keyword matching

Hybrid retrieval combines both, with a cross-encoder reranker to filter noise before the LLM generates an answer.

## Features

- **Hybrid Retrieval**: BM25 (keyword) + FAISS (semantic) search with deduplication
- **Cross-Encoder Reranking**: ms-marco-MiniLM-L-6-v2 for relevance scoring
- **Agentic RAG Pipeline**: Structured pipeline with retrieval → reranking → generation
- **Auditable Responses**: Returns answer + source documents for traceability
- **FastAPI Endpoint**: Production-ready REST API
- **Retrieval Evaluation**: Cosine similarity scoring and precision@k metrics

## Dataset

Synthetic P&C insurance policy documents covering:
- Homeowners (HO-3) policy with full coverage sections (A–F)
- Property and liability exclusions
- Commercial auto policy
- General liability policy
- Workers compensation policy
- Umbrella/excess liability policy
- Professional liability (E&O)
- Business owners policy (BOP)
- Cyber liability policy
- Inland marine / contractors equipment
- Endorsements (water backup, scheduled property, identity theft)
- Claims procedures and FNOL requirements

## Setup

```bash
# Clone the repo
git clone https://github.com/KalisettiRamyaSudha/agentic-rag-insurance.git
cd agentic-rag-insurance

# Install dependencies
pip install -r requirements.txt

# Build the vector store
python ingest.py

# Build the canonical document/chunk store (Phase 1 migration)
python scripts/build_canonical_store.py

# Run tests
python test_pipeline.py

# Run evaluation
python evaluation.py

# Start the API server
uvicorn app:app --reload
```

## API Usage

```bash
# Query the insurance knowledge base
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "What exclusions apply to flood damage?"}'
```

Response:
```json
{
  "answer": "Flood damage is excluded under Section 8.1...",
  "sources": ["SECTION 8: EXCLUSIONS - PROPERTY COVERAGE..."],
  "retrieval_count": 8
}
```

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Keyword Search | BM25 (rank_bm25) |
| Vector Search | FAISS + all-MiniLM-L6-v2 |
| Reranker | CrossEncoder ms-marco-MiniLM-L-6-v2 |
| LLM | OpenAI GPT-3.5-turbo |
| API | FastAPI |
| Orchestration | LangChain |
| Evaluation | scikit-learn, SentenceTransformers |

## Configuration

Set your OpenAI API key:
```bash
export OPENAI_API_KEY="your-key-here"
```

Without an API key, the system runs in local mode — returning retrieved context without LLM generation.

## Evaluation Results

Run `python evaluation.py` to evaluate retrieval quality across 8 insurance-domain test queries measuring:
- **Cosine Similarity**: Semantic alignment between query and retrieved documents
- **Precision@k**: Percentage of retrieved documents containing relevant keywords
