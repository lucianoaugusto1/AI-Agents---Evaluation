"""Evaluator (judge) abstraction.

    Evaluator
    ├── OpenAIJudge        (LLM-as-a-Judge, needs OPENAI_API_KEY)
    └── LocalJudge         (deterministic, always available)

Context Precision and Context Recall never go through a judge: they are
computed from `expected_relevant_document_ids` and are always deterministic.
Only Faithfulness and Answer Relevancy can use an LLM.
"""

from __future__ import annotations

import json
from typing import Protocol

from ..retriever import RetrievedDocument
from .answer_relevancy import ANSWER_RELEVANCY_PROMPT, local_answer_relevancy
from .base import MetricResult
from .faithfulness import FAITHFULNESS_PROMPT, local_faithfulness


class Evaluator(Protocol):
    name: str

    def faithfulness(self, question: str, contexts: list[RetrievedDocument], answer: str) -> MetricResult: ...
    def answer_relevancy(self, question: str, answer: str) -> MetricResult: ...


class LocalJudge:
    """Deterministic, offline judge. Same rubric, implemented with word overlap."""

    name = "local-deterministic"

    def faithfulness(self, question: str, contexts: list[RetrievedDocument], answer: str) -> MetricResult:
        return local_faithfulness(answer, contexts)

    def answer_relevancy(self, question: str, answer: str) -> MetricResult:
        return local_answer_relevancy(question, answer)


class OpenAIJudge:
    """LLM-as-a-Judge. Falls back to the local judge if a call or parse fails."""

    name = "openai-llm-judge"

    def __init__(self, model: str, api_key: str):
        from openai import OpenAI  # optional dependency

        self._client = OpenAI(api_key=api_key)
        self._model = model
        self._fallback = LocalJudge()

    def _ask(self, prompt: str) -> dict | None:
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[{"role": "user", "content": prompt}],
            )
            return json.loads(response.choices[0].message.content or "{}")
        except Exception as exc:  # network, quota, malformed JSON...
            print(f"  [judge] LLM call failed ({exc.__class__.__name__}), using local judge")
            return None

    def faithfulness(self, question: str, contexts: list[RetrievedDocument], answer: str) -> MetricResult:
        context_block = "\n\n".join(f"[{c.id}]\n{c.text}" for c in contexts)
        prompt = (
            FAITHFULNESS_PROMPT.replace("{question}", question)
            .replace("{context}", context_block)
            .replace("{answer}", answer)
        )
        data = self._ask(prompt)
        if data is None or "score" not in data:
            return self._fallback.faithfulness(question, contexts, answer)
        return MetricResult(
            float(data["score"]),
            str(data.get("reason", "")),
            [f"UNSUPPORTED: {c}" for c in data.get("unsupported_claims", [])],
        )

    def answer_relevancy(self, question: str, answer: str) -> MetricResult:
        prompt = (
            ANSWER_RELEVANCY_PROMPT.replace("{question}", question)
            .replace("{answer}", answer)
        )
        data = self._ask(prompt)
        if data is None or "score" not in data:
            return self._fallback.answer_relevancy(question, answer)
        return MetricResult(float(data["score"]), str(data.get("reason", "")))
