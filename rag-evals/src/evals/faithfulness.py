"""Faithfulness — evaluates the GENERATOR (is the answer grounded?).

    Faithfulness = supported claims / total claims

A "claim" is a sentence of the generated answer. The two implementations
below use the same definition, they only differ in who decides whether a
claim is supported:

* local  (deterministic): a claim is supported when at least
  `SUPPORT_THRESHOLD` of its content words appear in the retrieved context.
* OpenAI (LLM-as-a-Judge): the model extracts claims and judges each one.
"""

from __future__ import annotations

from ..generator import NOT_ENOUGH_INFO, split_sentences
from ..retriever import RetrievedDocument, tokenize
from .base import MetricResult

SUPPORT_THRESHOLD = 0.75

FAITHFULNESS_PROMPT = """You are evaluating the FAITHFULNESS of a RAG answer.

Given the question, the retrieved context and the generated answer:
1. Split the answer into atomic factual claims.
2. For each claim decide if it is fully supported by the retrieved context.
   A claim is unsupported if the context does not state it, even if the claim
   is plausible or true in the real world.
3. score = supported claims / total claims.

If the answer only says it does not have enough information, and the context
indeed does not answer the question, return score 1.0.

Return STRICT JSON:
{"score": <float 0..1>, "reason": "<one short sentence>",
 "unsupported_claims": ["<claim>", ...]}

QUESTION:
{question}

RETRIEVED CONTEXT:
{context}

GENERATED ANSWER:
{answer}
"""


def local_faithfulness(
    answer: str, contexts: list[RetrievedDocument]
) -> MetricResult:
    context_tokens = set()
    for ctx in contexts:
        context_tokens.update(tokenize(ctx.text))

    if answer.strip() == NOT_ENOUGH_INFO:
        # Refusing to answer invents nothing, so it is perfectly faithful.
        return MetricResult(1.0, "The answer makes no claim beyond the context.")

    claims = split_sentences(answer)
    if not claims:
        return MetricResult(0.0, "Empty answer.")

    supported, details, unsupported = 0, [], []
    for claim in claims:
        claim_tokens = set(tokenize(claim))
        if not claim_tokens:
            continue
        coverage = len(claim_tokens & context_tokens) / len(claim_tokens)
        ok = coverage >= SUPPORT_THRESHOLD
        supported += int(ok)
        label = "supported  " if ok else "UNSUPPORTED"
        details.append(f"{label} (context coverage {coverage:.2f}): {claim}")
        if not ok:
            unsupported.append(claim)

    score = supported / len(claims)
    explanation = f"{supported}/{len(claims)} claims supported by the retrieved context"
    if unsupported:
        explanation += f' | unsupported: "{unsupported[0]}"'
    return MetricResult(score, explanation, details)
