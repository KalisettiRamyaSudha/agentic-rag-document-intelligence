from rank_bm25 import BM25Okapi
from langchain.vectorstores import FAISS
from langchain.embeddings import HuggingFaceEmbeddings
import numpy as np

documents = open("data/documents.txt").read().split("\n")

tokenized_docs = [doc.split(" ") for doc in documents]

bm25 = BM25Okapi(tokenized_docs)

embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)

vectorstore = FAISS.load_local("vectorstore", embeddings)

def hybrid_search(query, k=3):

    tokens = query.split(" ")

    bm25_scores = bm25.get_scores(tokens)
    bm25_results = np.argsort(bm25_scores)[::-1][:k]

    vector_results = vectorstore.similarity_search(query, k=k)

    results = []

    for idx in bm25_results:
        results.append(documents[idx])

    for doc in vector_results:
        results.append(doc.page_content)

    return list(set(results))