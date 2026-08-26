"""Answer generation.

Two interchangeable generators:

* `LocalGenerator`  – deterministic, extractive, no API needed. It is the
  default so the workshop always works offline.
* `OpenAIGenerator` – a real LLM, enabled when OPENAI_API_KEY is set.

Both honour `STRICT_CONTEXT_PROMPT`, which is the second experiment of the
workshop.
"""

from __future__ import annotations

import re
from typing import Protocol

from .retriever import RetrievedDocument, tokenize

NOT_ENOUGH_INFO = (
    "The provided documentation does not contain enough information to answer "
    "this question."
)

STRICT_SYSTEM_PROMPT = (
    "You are a support assistant. Answer ONLY with information present in the "
    "provided context. Be direct and do not add background, opinions or "
    "marketing. If the context does not contain the answer, reply exactly: "
    f'"{NOT_ENOUGH_INFO}"'
)

LOOSE_SYSTEM_PROMPT = (
    "You are a friendly support assistant. Use the provided context, add "
    "helpful surrounding details, and always give the customer a confident "
    "answer even if the context is incomplete."
)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n{2,}", text)
    return [p.strip().replace("\n", " ") for p in parts if p.strip() and not p.strip().startswith("#")]


class Generator(Protocol):
    name: str

    def generate(self, question: str, contexts: list[RetrievedDocument], strict: bool) -> str: ...


class LocalGenerator:
    """Extractive generator: it re-uses sentences from the retrieved context.

    Non-strict mode is deliberately chatty (it keeps weakly related sentences
    and invents an answer when the context is thin), which is what makes
    Faithfulness and Answer Relevancy move in the experiments.
    """

    name = "local-extractive"

    #: minimum question-token overlap for a sentence to count as "on topic"
    RELEVANCE_THRESHOLD = 0.34

    def _ranked_sentences(self, question: str, contexts: list[RetrievedDocument]):
        q_tokens = set(tokenize(question))
        scored = []
        for ctx in contexts:
            for sentence in split_sentences(ctx.text):
                s_tokens = set(tokenize(sentence))
                if not s_tokens or not q_tokens:
                    continue
                overlap = len(q_tokens & s_tokens) / len(q_tokens)
                scored.append((overlap, sentence))
        scored.sort(key=lambda pair: (-pair[0], pair[1]))
        return scored

    def generate(self, question: str, contexts: list[RetrievedDocument], strict: bool) -> str:
        scored = self._ranked_sentences(question, contexts)
        best = scored[0][0] if scored else 0.0

        if strict:
            keep = [s for score, s in scored if score >= self.RELEVANCE_THRESHOLD][:2]
            return " ".join(keep) if keep else NOT_ENOUGH_INFO

        # Non-strict: keep three sentences even when they are only loosely
        # related, and never admit ignorance.
        keep = [s for _, s in scored[:3]]
        if best < self.RELEVANCE_THRESHOLD:
            # The context does not answer the question -> the chatty generator
            # makes something up. This is the hallucination we want to measure.
            return (
                "Yes, that is available. Our plans can be customised on request "
                "and unlimited usage is granted to customers who ask for it."
            )
        return " ".join(keep)


class OpenAIGenerator:
    name = "openai"

    def __init__(self, model: str, api_key: str):
        from openai import OpenAI  # imported lazily: optional dependency

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(self, question: str, contexts: list[RetrievedDocument], strict: bool) -> str:
        context_block = "\n\n".join(f"[{c.id}]\n{c.text}" for c in contexts)
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": STRICT_SYSTEM_PROMPT if strict else LOOSE_SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{context_block}\n\nQuestion: {question}"},
            ],
        )
        return (response.choices[0].message.content or "").strip()
