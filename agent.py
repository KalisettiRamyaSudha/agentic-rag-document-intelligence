from hybrid_retriever import hybrid_search
from reranker import rerank
from dotenv import load_dotenv
load_dotenv()

def agentic_rag(query):
    """
    Agentic RAG pipeline:
    1. Hybrid retrieval (BM25 + FAISS)
    2. Cross-encoder reranking
    3. LLM answer generation

    For local testing, this returns the reranked context.
    For production, integrate with OpenAI or any LLM API.
    """
    # Step 1: Hybrid retrieval
    retrieved_docs = hybrid_search(query)
    print(f"\n[Agent] Retrieved {len(retrieved_docs)} documents via hybrid search")

    # Step 2: Rerank with cross-encoder
    reranked_docs = rerank(query, retrieved_docs)
    print(f"[Agent] Reranked to top {len(reranked_docs)} documents")

    # Step 3: Build context
    context = "\n---\n".join(reranked_docs)

    # Step 4: Generate answer
    # Option A: Use OpenAI (requires API key)
    try:
        from openai import OpenAI
        import os
        if os.environ.get("OPENAI_API_KEY"):
            client = OpenAI()
            prompt = f"""You are an insurance policy expert. Use the context below to answer the question accurately.
If the answer is not in the context, say "I cannot find this information in the provided policy documents."

Context:
{context}

Question:
{query}

Answer:"""
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            return {
                "answer": response.choices[0].message.content,
                "sources": reranked_docs,
                "retrieval_count": len(retrieved_docs)
            }
    except Exception as e:
        print(f"OpenAI failed: {e}")
        pass

    # Option B: Return context-based response (no API key needed)
    return {
        "answer": f"[Local Mode - No LLM API key] Based on retrieved context:\n\n{context}",
        "sources": reranked_docs,
        "retrieval_count": len(retrieved_docs)
    }
