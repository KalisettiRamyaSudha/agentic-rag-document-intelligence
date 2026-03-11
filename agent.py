from hybrid_retriever import hybrid_search
from reranker import rerank
from openai import OpenAI

client = OpenAI()

def agentic_rag(query):

    retrieved_docs = hybrid_search(query)

    reranked_docs = rerank(query, retrieved_docs)

    context = "\n".join(reranked_docs)

    prompt = f"""
Use the context below to answer the question.

Context:
{context}

Question:
{query}

Answer:
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content