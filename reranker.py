from sentence_transformers import CrossEncoder

reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank(query, docs, top_k=3):
    """
    Rerank retrieved documents using a cross-encoder model.
    Returns the top_k most relevant documents.
    """
    if not docs:
        return []

    pairs = [[query, doc] for doc in docs]
    scores = reranker.predict(pairs)

    ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)

    return [doc for doc, score in ranked[:top_k]]
