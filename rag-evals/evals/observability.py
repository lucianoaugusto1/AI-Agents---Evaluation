"""Observabilidade da suite: none, local (JSONL) ou Langfuse.

No Langfuse cada caso vira um trace com dois spans filhos, `retrieve` e
`generate`, e os scores das cinco metricas ficam no span do caso. E assim que
o participante ve qual chunk entrou no prompt e por que a resposta saiu errada.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Protocol

from acme_cloud_rag import RagResult
from acme_cloud_rag.llm import load_env_file

from .judge import CaseResult

ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"


class EvalObserver(Protocol):
    def start_run(self, metadata: dict[str, Any]) -> None: ...
    def log_case(self, case: dict[str, Any], result: CaseResult, rag: RagResult) -> None: ...
    def end_run(self, summary: dict[str, Any]) -> None: ...


def _retrieval_payload(rag: RagResult) -> list[dict[str, Any]]:
    return [
        {
            "chunk_id": item.chunk.chunk_id,
            "doc_id": item.doc_id,
            "score": round(item.score, 3),
            "is_obsolete": item.chunk.is_obsolete,
            "text": item.chunk.text,
        }
        for item in rag.retrieved
    ]


def _scores(result: CaseResult) -> dict[str, float]:
    return {
        "overall": result.total,
        "context_precision": result.context_precision,
        "context_recall": result.context_recall,
        "faithfulness": result.faithfulness,
        "answer_relevancy": result.answer_relevancy,
        "format": result.format,
    }


class NoopObserver:
    def start_run(self, metadata: dict[str, Any]) -> None:
        pass

    def log_case(self, case: dict[str, Any], result: CaseResult, rag: RagResult) -> None:
        pass

    def end_run(self, summary: dict[str, Any]) -> None:
        pass


class LocalJsonlObserver:
    def __init__(self) -> None:
        RUNS_DIR.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.path = RUNS_DIR / f"rag-eval-run-{stamp}.jsonl"

    def _write(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    def start_run(self, metadata: dict[str, Any]) -> None:
        self._write({"event": "run_started", "metadata": metadata})

    def log_case(self, case: dict[str, Any], result: CaseResult, rag: RagResult) -> None:
        self._write(
            {
                "event": "case_evaluated",
                "case_id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "retrieval": _retrieval_payload(rag),
                "context": rag.context,
                "response": rag.raw_response,
                "scores": _scores(result),
                "problems": result.problems,
            }
        )

    def end_run(self, summary: dict[str, Any]) -> None:
        self._write({"event": "run_finished", "summary": summary})
        print(f"trace local gravado em {self.path}")


class LangfuseObserver:
    def __init__(self) -> None:
        load_env_file()
        from langfuse import get_client

        self.client = get_client()
        self.metadata: dict[str, Any] = {}

    def start_run(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata

    def log_case(self, case: dict[str, Any], result: CaseResult, rag: RagResult) -> None:
        with self.client.start_as_current_observation(
            as_type="span",
            name=f"rag-eval:{case['id']}",
            input={"question": case["question"], "category": case["category"]},
            metadata={**self.metadata, "expected_document_ids": case["expected_document_ids"]},
        ) as span:
            with self.client.start_as_current_observation(
                as_type="span",
                name="retrieve",
                input={"query": case["question"]},
            ) as retrieval:
                retrieval.update(
                    output={"chunks": _retrieval_payload(rag)},
                    metadata={
                        "retrieved_doc_ids": rag.retrieved_doc_ids,
                        "expected_document_ids": case["expected_document_ids"],
                    },
                )

            with self.client.start_as_current_observation(
                as_type="generation",
                name="generate",
                input=rag.prompt,
                model=rag.model,
            ) as generation:
                generation.update(output=rag.raw_response)

            span.update(output=rag.raw_response, metadata={"problems": result.problems})
            for name, value in _scores(result).items():
                span.score(name=name, value=value, data_type="NUMERIC")

    def end_run(self, summary: dict[str, Any]) -> None:
        self.client.flush()
        print("scores enviados para o Langfuse")


def create_observer(provider: str) -> EvalObserver:
    selected = provider.lower().strip()
    if selected == "none":
        return NoopObserver()
    if selected == "local":
        return LocalJsonlObserver()
    if selected == "langfuse":
        return LangfuseObserver()
    raise ValueError(f"trace provider desconhecido: {provider}")
