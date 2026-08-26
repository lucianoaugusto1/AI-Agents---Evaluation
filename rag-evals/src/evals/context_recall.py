"""Context Recall — evaluates the RETRIEVER's coverage.

    Context Recall = (expected documents that were retrieved) / (expected documents)

It answers a single question: did retrieval bring back everything the answer
needs? Multi-document test cases are the ones that expose a low recall, and
raising TOP_K is the usual way to fix it.
"""

from __future__ import annotations

from ..retriever import RetrievedDocument
from .base import MetricResult


def context_recall(
    retrieved: list[RetrievedDocument], expected_ids: list[str]
) -> MetricResult:
    if not expected_ids:
        return MetricResult(1.0, "No expected documents declared for this case.")

    retrieved_ids = {doc.id for doc in retrieved}
    found = [doc_id for doc_id in expected_ids if doc_id in retrieved_ids]
    missing = [doc_id for doc_id in expected_ids if doc_id not in retrieved_ids]

    details = [f"expected: {', '.join(expected_ids)}"]
    details.append(f"retrieved: {', '.join(d.id for d in retrieved) or '-'}")
    if missing:
        details.append(f"MISSING: {', '.join(missing)}")

    score = len(found) / len(expected_ids)
    explanation = f"{len(found)}/{len(expected_ids)} expected documents retrieved"
    return MetricResult(score, explanation, details)
