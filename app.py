from fastapi import FastAPI
from pydantic import BaseModel
from agent import agentic_rag

app = FastAPI()

class Query(BaseModel):
    question: str

@app.post("/ask")

def ask(q: Query):

    answer = agentic_rag(q.question)

    return {"answer": answer}