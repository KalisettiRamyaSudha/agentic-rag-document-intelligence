from rank_bm25 import BM25Okapi
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
import numpy as np
from sklearn.preprocessing import StandardScaler

documents = open("data/documents.txt").read().split("\n")
# Filter empty lines
documents = [doc for doc in documents if doc.strip()]

tokenized_docs = [doc.lower().split(" ") for doc in documents]

bm25 = BM25Okapi(tokenized_docs)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = FAISS.load_local(
    "vectorstore", embeddings, allow_dangerous_deserialization=True
)

def hybrid_search(query, k=7):
    """
    Hybrid search combining BM25 (keyword) and FAISS (semantic) retrieval.
    Returns deduplicated results from both retrievers.
    """
    # BM25 keyword search
    tokens = query.lower().split(" ")
    bm25_scores = bm25.get_scores(tokens)
    bm25_norm = (bm25_scores - bm25_scores.min()) / (bm25_scores.max() - bm25_scores.min() + 1e-8)


    # FAISS vector search
    vector_results = vectorstore.similarity_search_with_score(query, k=k)

    # Build a combined score dict
    combined = {}

    for idx in range(len(documents)):
        if bm25_norm[idx] > 0.1:  # only consider relevant BM25 hits
            combined[documents[idx]] = 0.4 * bm25_norm[idx]

    for doc, faiss_score in vector_results:
        text = doc.page_content
        # FAISS returns distance (lower = better), convert to similarity
        sim = 1 / (1 + faiss_score)
        if text in combined:
            combined[text] += 0.6 * sim
        else:
            combined[text] = 0.6 * sim

    # Sort by combined score and return top results
    ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, score in ranked[:k]]
