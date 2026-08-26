"""The RAG pipeline and the wiring that decides local vs LLM mode.

    Question -> Retriever -> Top-K documents -> Generator -> Answer
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from . import config
from .evals.judges import Evaluator, LocalJudge, OpenAIJudge
from .generator import Generator, LocalGenerator, OpenAIGenerator
from .retriever import BM25Retriever, RetrievedDocument, load_documents

load_dotenv(config.ROOT / ".env")  # missing .env is fine: local mode still works


@dataclass
class RagAnswer:
    question: str
    contexts: list[RetrievedDocument]
    answer: str


@dataclass
class TestCase:
    id: str
    question: str
    expected_answer: str
    expected_relevant_document_ids: list[str]
    category: str = "simple"
    notes: str = ""


class RagPipeline:
    def __init__(self, top_k: int | None = None, strict: bool | None = None,
                 generator: Generator | None = None):
        self.top_k = config.TOP_K if top_k is None else top_k
        self.strict = config.STRICT_CONTEXT_PROMPT if strict is None else strict
        self.retriever = BM25Retriever(load_documents())
        self.generator = generator or build_generator()

    def answer(self, question: str) -> RagAnswer:
        contexts = self.retriever.retrieve(question, self.top_k)
        answer = self.generator.generate(question, contexts, self.strict)
        return RagAnswer(question=question, contexts=contexts, answer=answer)


def _resolve_mode() -> str:
    """Return 'openai' or 'local', respecting EVAL_MODE and the API key."""
    mode, key = config.eval_mode(), config.openai_api_key()
    if mode not in {"auto", "local", "openai"}:
        raise ValueError(f"EVAL_MODE must be auto, local or openai (got '{mode}').")
    if mode == "local":
        return "local"
    if mode == "openai":
        if not key:
            raise RuntimeError(
                "EVAL_MODE=openai but OPENAI_API_KEY is missing. "
                "Add it to .env (see .env.example) or use EVAL_MODE=local."
            )
        return "openai"
    return "openai" if key else "local"


def build_generator() -> Generator:
    if _resolve_mode() == "openai":
        try:
            return OpenAIGenerator(config.eval_model(), config.openai_api_key() or "")
        except ImportError:
            print("[warn] openai package not installed, using the local generator.")
    return LocalGenerator()


def build_judge() -> Evaluator:
    if _resolve_mode() == "openai":
        try:
            return OpenAIJudge(config.eval_model(), config.openai_api_key() or "")
        except ImportError:
            print("[warn] openai package not installed, using the local judge.")
    return LocalJudge()


def load_dataset(path: Path | None = None) -> list[TestCase]:
    path = path or config.DATASET_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Evaluation dataset not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSON: {exc}") from exc

    cases = raw.get("cases") if isinstance(raw, dict) else raw
    if not isinstance(cases, list) or not cases:
        raise ValueError(f"{path} must contain a non-empty list of cases.")

    parsed: list[TestCase] = []
    known_ids = {d.id for d in load_documents()}
    for i, case in enumerate(cases):
        missing = [f for f in ("id", "question", "expected_answer",
                               "expected_relevant_document_ids") if f not in case]
        if missing:
            raise ValueError(f"Case #{i} is missing required field(s): {', '.join(missing)}")
        unknown = set(case["expected_relevant_document_ids"]) - known_ids
        if unknown:
            raise ValueError(
                f"Case '{case['id']}' references unknown document(s): {', '.join(sorted(unknown))}"
            )
        parsed.append(
            TestCase(
                id=case["id"],
                question=case["question"],
                expected_answer=case["expected_answer"],
                expected_relevant_document_ids=list(case["expected_relevant_document_ids"]),
                category=case.get("category", "simple"),
                notes=case.get("notes", ""),
            )
        )
    return parsed
