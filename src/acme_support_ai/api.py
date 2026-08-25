from __future__ import annotations

from statistics import mean

from fastapi import FastAPI
from pydantic import BaseModel

from evals.run_eval import run
from .orchestrator import answer_question


app = FastAPI(
    title="ACME Support AI",
    description="Simulated multi-agent internal support assistant for an Evaluation workshop.",
    version="0.1.0",
)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    raw_response: str


class EvalRunRequest(BaseModel):
    trace_provider: str = "local"


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    return AskResponse(raw_response=answer_question(request.question))


@app.post("/eval/run")
def run_eval(request: EvalRunRequest) -> dict:
    results = run(trace_provider=request.trace_provider)
    return {
        "overall": mean(result.total for result in results),
        "metrics": {
            "relevance": mean(result.relevance for result in results),
            "faithfulness": mean(result.faithfulness for result in results),
            "format": mean(result.format for result in results),
            "safety": mean(result.safety for result in results),
        },
        "cases": [result.__dict__ for result in results],
    }
