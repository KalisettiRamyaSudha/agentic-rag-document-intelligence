from fastapi import FastAPI
from pydantic import BaseModel
from agent import agentic_rag

app = FastAPI(
    title="Insurance Policy RAG API",
    description="Agentic RAG system for P&C insurance policy document intelligence",
    version="1.0.0"
)

class Query(BaseModel):
    question: str

class Answer(BaseModel):
    answer: str
    sources: list[str]
    retrieval_count: int

@app.post("/ask", response_model=Answer)
def ask(q: Query):
    """Query the insurance policy knowledge base."""
    result = agentic_rag(q.question)
    return result

@app.get("/health")
def health():
    return {"status": "healthy", "model": "hybrid-rag-v1"}
