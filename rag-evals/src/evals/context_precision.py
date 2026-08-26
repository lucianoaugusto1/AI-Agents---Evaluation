"""Context Precision — evaluates the RETRIEVER's ranking.

Formula (documented so nothing is a black box):

    Context Precision = (1 / K) * sum_{i=1..K} Precision@i

    Precision@i = (relevant documents among the first i) / i

`K` is the number of retrieved documents (TOP_K) and a document is relevant
when its id is listed in `expected_relevant_document_ids` for that test case.

Why this formula:

* It is order aware — a relevant document at rank 1 contributes to every
  Precision@i, one at rank 5 contributes to almost nothing. Plain
  `relevant / retrieved` would ignore ranking entirely.
* It is noise aware — every extra irrelevant document you retrieve drags the
  average down. This is what makes a larger TOP_K visibly cost precision.
"""

from __future__ import annotations

from ..retriever import RetrievedDocument
from .base import MetricResult


def context_precision(
    retrieved: list[RetrievedDocument], expected_ids: list[str]
) -> MetricResult:
    if not retrieved:
        return MetricResult(0.0, "No documents were retrieved.")

    expected = set(expected_ids)
    hits = 0
    precisions_at_i: list[float] = []
    details: list[str] = []

    for i, doc in enumerate(retrieved, start=1):
        relevant = doc.id in expected
        hits += int(relevant)
        p_at_i = hits / i
        precisions_at_i.append(p_at_i)
        details.append(
            f"{i}. {doc.id:<24} {'relevant  ' if relevant else 'irrelevant'} "
            f"P@{i}={p_at_i:.2f}"
        )

    score = sum(precisions_at_i) / len(precisions_at_i)
    explanation = (
        "mean(P@1..P@K) = ("
        + " + ".join(f"{p:.2f}" for p in precisions_at_i)
        + f") / {len(precisions_at_i)}"
    )
    return MetricResult(score, explanation, details)
