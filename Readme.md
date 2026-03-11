Overview

This project implements an Agentic Retrieval-Augmented Generation (RAG) system that combines hybrid retrieval, cross-encoder reranking, and LLM reasoning to answer questions over document collections.

**Features**

1. Hybrid retrieval (BM25 + vector search)
2. Cross-encoder reranking
3. Agentic retrieval workflow
4. FastAPI inference API
5. Retrieval quality evaluation

**Architecture:**
        
User Query -> Hybrid Retriever
(BM25 + FAISS) -> Cross Encoder Reranker -> LLM ->
Answer


**Tech Stack**:
`Python,LangChain,
FAISS,
Sentence Transformers
FastAPI,
OpenAI,
scikit-learn`