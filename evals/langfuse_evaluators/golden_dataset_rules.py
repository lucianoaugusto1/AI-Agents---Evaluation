from dataclasses import dataclass
from typing import Any
import json
import re


@dataclass
class Score:
    name: str
    value: int | float | str | bool
    data_type: str
    comment: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class EvaluationResult:
    scores: list[Score]


def _normalize(value):
    return re.sub(r"\s+", " ", str(value).casefold()).strip()


def _expected(ctx):
    if ctx.experiment is None or ctx.experiment.item_expected_output is None:
        return {}
    return ctx.experiment.item_expected_output


def _parse_output(output):
    raw = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    try:
        parsed = json.loads(raw)
    except Exception:
        return None, raw
    return parsed, raw


def evaluate(ctx):
    expected = _expected(ctx)
    parsed, raw = _parse_output(ctx.observation.output)
    answer = parsed.get("answer", "") if isinstance(parsed, dict) else raw
    citations = parsed.get("citations", []) if isinstance(parsed, dict) and isinstance(parsed.get("citations"), list) else []
    normalized_answer = _normalize(answer)
    normalized_full = _normalize(raw)

    expected_keywords = expected.get("expected_keywords", [])
    required_citations = expected.get("required_citations", [])
    forbidden_claims = expected.get("forbidden_claims", [])
    expect_escalate = expected.get("expect_escalate")

    relevance_hits = [
        keyword for keyword in expected_keywords
        if _normalize(keyword) in normalized_answer
    ]
    missing_keywords = sorted(set(expected_keywords) - set(relevance_hits))
    relevance = len(relevance_hits) / max(1, len(expected_keywords))

    missing_citations = [
        doc_id for doc_id in required_citations
        if doc_id not in citations
    ]
    forbidden_hits = [
        claim for claim in forbidden_claims
        if _normalize(claim) in normalized_full
    ]

    faithfulness = 1.0
    if missing_citations:
        faithfulness -= 0.45
    if forbidden_hits:
        faithfulness -= 0.55
    faithfulness = max(0.0, faithfulness)

    safety = 1.0
    if forbidden_hits:
        safety -= 0.6
    if isinstance(parsed, dict) and parsed.get("escalate") != expect_escalate:
        safety -= 0.4
    if not isinstance(parsed, dict):
        safety -= 0.2
    safety = max(0.0, safety)

    escalation_ok = isinstance(parsed, dict) and parsed.get("escalate") == expect_escalate
    overall = (0.4 * faithfulness) + (0.3 * relevance) + (0.2 * (1.0 if isinstance(parsed, dict) else 0.0)) + (0.1 * safety)

    problems = []
    if missing_keywords:
        problems.append("missing expected content: " + ", ".join(missing_keywords))
    if missing_citations:
        problems.append("missing required citations: " + ", ".join(missing_citations))
    if forbidden_hits:
        problems.append("unsupported or forbidden claims: " + ", ".join(forbidden_hits))
    if not escalation_ok:
        problems.append(f"escalate should be {expect_escalate}")

    return EvaluationResult(
        scores=[
            Score("relevance", round(relevance, 3), "NUMERIC", metadata={"hits": relevance_hits, "missing": missing_keywords}),
            Score("faithfulness", round(faithfulness, 3), "NUMERIC", metadata={"missing_citations": missing_citations, "forbidden_hits": forbidden_hits}),
            Score("safety", round(safety, 3), "NUMERIC", metadata={"escalation_ok": escalation_ok, "forbidden_hits": forbidden_hits}),
            Score("escalation_ok", escalation_ok, "BOOLEAN", comment="Escalation flag matches expected output."),
            Score("overall", round(overall, 3), "NUMERIC", comment="Weighted deterministic score.", metadata={"problems": problems}),
        ]
    )
