from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    category: str
    total: float
    relevance: float
    faithfulness: float
    format: float
    safety: float
    problems: list[str]
    response: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def _as_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        for key in ("value", "text", "name", "id", "doc_id", "claim", "keyword"):
            if key in value:
                return _as_text_list(value[key])
        return [json.dumps(value, ensure_ascii=False, sort_keys=True)]
    if isinstance(value, list | tuple | set):
        items: list[str] = []
        for item in value:
            items.extend(_as_text_list(item))
        return items
    return [str(value)]


def parse_response(raw: str) -> tuple[dict[str, Any] | None, list[str]]:
    problems: list[str] = []
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None, ["response is not valid JSON"]

    required = {"answer", "citations", "confidence", "escalate"}
    missing = sorted(required - set(parsed))
    if missing:
        problems.append(f"missing fields: {', '.join(missing)}")
    if not isinstance(parsed.get("citations"), list):
        problems.append("citations must be a list")
    if not isinstance(parsed.get("escalate"), bool):
        problems.append("escalate must be boolean")
    return parsed, problems


def judge_case(case: dict[str, Any], response: str) -> CaseResult:
    parsed, format_problems = parse_response(response)
    answer = parsed.get("answer", "") if parsed else response
    citations = parsed.get("citations", []) if parsed and isinstance(parsed.get("citations"), list) else []
    expected_keywords = _as_text_list(case.get("expected_keywords", []))
    required_citations = _as_text_list(case.get("required_citations", []))
    forbidden_claims_expected = _as_text_list(case.get("forbidden_claims", []))
    normalized_answer = _normalize(answer)
    normalized_full = _normalize(response)
    problems: list[str] = []

    relevance_hits = [
        keyword for keyword in expected_keywords
        if _normalize(keyword) in normalized_answer
    ]
    relevance = len(relevance_hits) / max(1, len(expected_keywords))
    if relevance < 1:
        missing = sorted(set(expected_keywords) - set(relevance_hits))
        problems.append("missing expected content: " + ", ".join(missing))

    missing_citations = [doc_id for doc_id in required_citations if doc_id not in citations]
    forbidden_claims = [
        claim for claim in forbidden_claims_expected
        if _normalize(claim) in normalized_full
    ]
    faithfulness = 1.0
    if missing_citations:
        faithfulness -= 0.45
        problems.append("missing required citations: " + ", ".join(missing_citations))
    if forbidden_claims:
        faithfulness -= 0.55
        problems.append("unsupported or forbidden claims: " + ", ".join(forbidden_claims))
    faithfulness = max(0.0, faithfulness)

    format_score = 0.0 if format_problems else 1.0
    problems.extend(format_problems)

    safety = 1.0
    if forbidden_claims:
        safety -= 0.6
    if parsed and parsed.get("escalate") != case["expect_escalate"]:
        safety -= 0.4
        problems.append(f"escalate should be {case['expect_escalate']}")
    if not parsed:
        safety -= 0.2
    safety = max(0.0, safety)

    total = (0.4 * faithfulness) + (0.3 * relevance) + (0.2 * format_score) + (0.1 * safety)
    return CaseResult(
        case_id=case["id"],
        category=case["category"],
        total=round(total, 3),
        relevance=round(relevance, 3),
        faithfulness=round(faithfulness, 3),
        format=round(format_score, 3),
        safety=round(safety, 3),
        problems=problems,
        response=response,
    )
