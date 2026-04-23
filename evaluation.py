from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieval_score(query, retrieved_docs):
    """Calculate average cosine similarity between query and retrieved docs."""
    if not retrieved_docs:
        return 0.0

    q_emb = model.encode([query])
    doc_emb = model.encode(retrieved_docs)
    scores = cosine_similarity(q_emb, doc_emb)

    return float(scores.mean())

def retrieval_precision_at_k(query, retrieved_docs, relevant_keywords):
    """
    Estimate precision@k by checking if retrieved docs contain relevant keywords.
    """
    if not retrieved_docs:
        return 0.0

    relevant_count = 0
    for doc in retrieved_docs:
        doc_lower = doc.lower()
        if any(kw.lower() in doc_lower for kw in relevant_keywords):
            relevant_count += 1

    return relevant_count / len(retrieved_docs)

def evaluate_queries(test_cases):
    """
    Run evaluation on a set of test queries.
    Each test case: {"query": str, "keywords": list[str]}
    """
    results = []
    for tc in test_cases:
        from hybrid_retriever import hybrid_search
        from reranker import rerank

        retrieved = hybrid_search(tc["query"])
        reranked = rerank(tc["query"], retrieved)

        sim_score = retrieval_score(tc["query"], reranked)
        precision = retrieval_precision_at_k(tc["query"], reranked, tc["keywords"])

        results.append({
            "query": tc["query"],
            "similarity": round(sim_score, 4),
            "precision": round(precision, 4),
            "num_retrieved": len(retrieved),
            "num_reranked": len(reranked)
        })
        print(f"\nQuery: {tc['query']}")
        print(f"  Similarity: {sim_score:.4f} | Precision: {precision:.4f}")
        print(f"  Retrieved: {len(retrieved)} -> Reranked: {len(reranked)}")

    avg_sim = np.mean([r["similarity"] for r in results])
    avg_prec = np.mean([r["precision"] for r in results])
    print(f"\n{'='*60}")
    print(f"Average Similarity: {avg_sim:.4f}")
    print(f"Average Precision:  {avg_prec:.4f}")

    return results


if __name__ == "__main__":
    # Insurance-domain test cases
    test_cases = [
        {
            "query": "What does flood exclusion mean in homeowners insurance?",
            "keywords": ["flood", "surface water", "excluded", "NFIP"]
        },
        {
            "query": "What is covered under personal property coverage?",
            "keywords": ["personal property", "Coverage C", "owned", "insured"]
        },
        {
            "query": "How do I file a claim after property damage?",
            "keywords": ["claim", "FNOL", "report", "notice", "adjuster"]
        },
        {
            "query": "What is the liability limit for the commercial auto policy?",
            "keywords": ["commercial auto", "liability", "combined single limit", "$1,000,000"]
        },
        {
            "query": "Does the policy cover mold damage?",
            "keywords": ["mold", "fungus", "excluded", "endorsement"]
        },
        {
            "query": "What is an umbrella policy and what does it cover?",
            "keywords": ["umbrella", "excess", "ultimate net loss", "retained limit"]
        },
        {
            "query": "What are the workers compensation classification codes?",
            "keywords": ["workers compensation", "classification", "code", "carpentry", "payroll"]
        },
        {
            "query": "What does the cyber liability policy cover?",
            "keywords": ["cyber", "data breach", "network security", "privacy"]
        },
    ]

    print("="*60)
    print("RAG RETRIEVAL EVALUATION - P&C Insurance Documents")
    print("="*60)
    evaluate_queries(test_cases)
