"""Answer Relevancy — evaluates the GENERATOR (does it answer the question?).

Deterministic version:

    Answer Relevancy = 0.5 * coverage + 0.5 * focus

    coverage = question keywords present in the answer / question keywords
    focus    = answer sentences that are on topic / answer sentences

`coverage` punishes answers that dodge the question, `focus` punishes padding
(extra sentences that do not address what was asked). A non-committal answer
("not enough information") scores 0, following the usual convention: it may
be faithful, but it does not answer the user.
"""

from __future__ import annotations

from ..generator import NOT_ENOUGH_INFO, split_sentences
from ..retriever import tokenize
from .base import MetricResult

ON_TOPIC_THRESHOLD = 0.25

ANSWER_RELEVANCY_PROMPT = """You are evaluating the ANSWER RELEVANCY of a RAG answer.

Judge only whether the answer addresses the user's question:
- does it answer what was asked (directly, without dodging)?
- is it free of padding and unrelated content?
Do NOT reward or punish factual correctness here, that is Faithfulness.

A non-committal answer ("I don't have enough information") scores 0.0.

Return STRICT JSON:
{"score": <float 0..1>, "reason": "<one short sentence>"}

QUESTION:
{question}

GENERATED ANSWER:
{answer}
"""


def local_answer_relevancy(question: str, answer: str) -> MetricResult:
    if answer.strip() == NOT_ENOUGH_INFO:
        return MetricResult(
            0.0, "Non-committal answer: faithful, but it does not answer the user."
        )

    q_tokens = set(tokenize(question))
    a_tokens = set(tokenize(answer))
    if not q_tokens or not a_tokens:
        return MetricResult(0.0, "Empty question or answer.")

    coverage = len(q_tokens & a_tokens) / len(q_tokens)

    sentences = split_sentences(answer)
    on_topic = [
        s for s in sentences
        if q_tokens and len(set(tokenize(s)) & q_tokens) / len(q_tokens) >= ON_TOPIC_THRESHOLD
    ]
    focus = len(on_topic) / len(sentences) if sentences else 0.0

    score = 0.5 * coverage + 0.5 * focus
    details = [
        f"coverage = {coverage:.2f} (question keywords found in the answer)",
        f"focus    = {focus:.2f} ({len(on_topic)}/{len(sentences)} sentences on topic)",
    ]
    return MetricResult(score, "0.5 * coverage + 0.5 * focus", details)
