from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Protocol

from .judge import CaseResult
from src.acme_support_ai.config import load_env_file


ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = ROOT / "runs"


class EvalObserver(Protocol):
    def start_run(self, metadata: dict[str, Any]) -> None:
        ...

    def log_case(self, case: dict[str, Any], result: CaseResult) -> None:
        ...

    def end_run(self, summary: dict[str, Any]) -> None:
        ...


class NoopObserver:
    def start_run(self, metadata: dict[str, Any]) -> None:
        pass

    def log_case(self, case: dict[str, Any], result: CaseResult) -> None:
        pass

    def end_run(self, summary: dict[str, Any]) -> None:
        pass


class LocalJsonlObserver:
    def __init__(self) -> None:
        RUNS_DIR.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.path = RUNS_DIR / f"eval-run-{stamp}.jsonl"

    def _write(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=False) + "\n")

    def start_run(self, metadata: dict[str, Any]) -> None:
        self._write({"event": "run_started", "metadata": metadata})

    def log_case(self, case: dict[str, Any], result: CaseResult) -> None:
        self._write(
            {
                "event": "case_evaluated",
                "case_id": case["id"],
                "category": case["category"],
                "question": case["question"],
                "scores": {
                    "total": result.total,
                    "relevance": result.relevance,
                    "faithfulness": result.faithfulness,
                    "format": result.format,
                    "safety": result.safety,
                },
                "problems": result.problems,
                "response": result.response,
            }
        )

    def end_run(self, summary: dict[str, Any]) -> None:
        self._write({"event": "run_finished", "summary": summary})
        print(f"local trace written to {self.path}")


class LangfuseObserver:
    def __init__(self) -> None:
        load_env_file()
        from langfuse import get_client

        self.client = get_client()

    def start_run(self, metadata: dict[str, Any]) -> None:
        self.metadata = metadata

    def log_case(self, case: dict[str, Any], result: CaseResult) -> None:
        with self.client.start_as_current_observation(
            as_type="span",
            name=f"eval:{case['id']}",
            input={"question": case["question"], "category": case["category"]},
            metadata=self.metadata,
        ) as span:
            span.update(output=result.response)
            span.score(name="overall", value=result.total, data_type="NUMERIC")
            span.score(name="relevance", value=result.relevance, data_type="NUMERIC")
            span.score(name="faithfulness", value=result.faithfulness, data_type="NUMERIC")
            span.score(name="format", value=result.format, data_type="NUMERIC")
            span.score(name="safety", value=result.safety, data_type="NUMERIC")

    def end_run(self, summary: dict[str, Any]) -> None:
        self.client.flush()
        print("langfuse trace flush requested")


def create_observer(provider: str) -> EvalObserver:
    selected = provider.lower().strip()
    if selected == "none":
        return NoopObserver()
    if selected == "local":
        return LocalJsonlObserver()
    if selected == "langfuse":
        return LangfuseObserver()
    raise ValueError(f"unknown trace provider: {provider}")
