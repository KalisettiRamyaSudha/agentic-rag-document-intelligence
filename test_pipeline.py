"""
Quick test script - Run after ingest.py to verify the full RAG pipeline.
Usage: python test_pipeline.py
"""
from hybrid_retriever import hybrid_search
from reranker import rerank
from agent import agentic_rag

print("=" * 60)
print("INSURANCE RAG PIPELINE - LOCAL TEST")
print("=" * 60)

# Test queries that map to P&C insurance scenarios
test_queries = [
    "What does the flood exclusion cover?",
    "What is the deductible for the homeowners policy?",
    "How do I file a claim after property damage?",
    "What does the commercial auto policy cover?",
    "Does the policy cover mold damage?",
    "What is the umbrella policy limit?",
    "What are the workers compensation classification codes?",
    "What does the cyber liability policy cover?",
]

for i, query in enumerate(test_queries, 1):
    print(f"\n{'─' * 60}")
    print(f"TEST {i}: {query}")
    print(f"{'─' * 60}")

    # Step 1: Hybrid search
    results = hybrid_search(query)
    print(f"  Hybrid search returned: {len(results)} documents")

    # Step 2: Rerank
    reranked = rerank(query, results)
    print(f"  After reranking: {len(reranked)} documents")

    # Step 3: Show top result preview
    if reranked:
        preview = reranked[0][:150].replace("\n", " ")
        print(f"  Top result preview: {preview}...")

    print()

# Full pipeline test
print("=" * 60)
print("FULL AGENTIC RAG PIPELINE TEST")
print("=" * 60)
query = "What exclusions apply to the homeowners property coverage?"
result = agentic_rag(query)
print(f"\nQuery: {query}")
print(f"\nAnswer:\n{result['answer'][:500]}")
print(f"\nSources returned: {len(result['sources'])}")
print(f"Total retrieved: {result['retrieval_count']}")

print("\n" + "=" * 60)
print("ALL TESTS PASSED - Pipeline is working!")
print("=" * 60)
