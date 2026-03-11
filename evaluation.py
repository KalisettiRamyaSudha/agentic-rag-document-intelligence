from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieval_score(query, retrieved_docs):

    q_emb = model.encode([query])

    doc_emb = model.encode(retrieved_docs)

    scores = cosine_similarity(q_emb, doc_emb)

    return scores.mean()