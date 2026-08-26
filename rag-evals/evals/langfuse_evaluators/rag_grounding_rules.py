from dataclasses import dataclass
from typing import Any
import json
import re
import unicodedata


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


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


def evaluate(ctx):
    expected = ctx.expected_output or {}
    output = ctx.observation.output
    raw = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)

    try:
        parsed = json.loads(raw)
    except Exception:
        parsed = None

    answer = parsed.get("answer", raw) if isinstance(parsed, dict) else raw
    citations = parsed.get("citations", []) if isinstance(parsed, dict) else []
    citations = [str(item) for item in citations] if isinstance(citations, list) else []
    refused = bool(parsed.get("refused")) if isinstance(parsed, dict) else False

    normalized_answer = _normalize(answer)
    problems = []

    keywords = expected.get("expected_keywords") or []
    hits = [word for word in keywords if _normalize(word) in normalized_answer]
    coverage = len(hits) / len(keywords) if keywords else 1.0
    if keywords and len(hits) < len(keywords):
        missing = [word for word in keywords if word not in hits]
        problems.append("conteudo esperado ausente: " + ", ".join(missing))

    forbidden = [claim for claim in (expected.get("forbidden_claims") or []) if _normalize(claim) in normalized_answer]
    if forbidden:
        problems.append("afirmacoes proibidas: " + ", ".join(forbidden))

    cited_docs = {item.split("#")[0] for item in citations}
    required_docs = expected.get("expected_document_ids") or []
    uncited = [doc for doc in required_docs if doc not in cited_docs]
    if uncited and not refused:
        problems.append("documentos nao citados: " + ", ".join(uncited))

    expect_refusal = bool(expected.get("expect_refusal"))
    if refused != expect_refusal:
        problems.append(f"refused deveria ser {expect_refusal}")

    grounding = coverage
    if forbidden:
        grounding = 0.0
    elif uncited and not refused:
        grounding = max(0.0, grounding - 0.45)

    return EvaluationResult(
        scores=[
            Score(
                name="grounding_rules",
                value=round(grounding, 3),
                data_type="NUMERIC",
                comment="OK" if not problems else "; ".join(problems),
                metadata={"problems": problems, "citations": citations},
            ),
            Score(
                name="forbidden_claim",
                value=bool(forbidden),
                data_type="BOOLEAN",
                comment="; ".join(forbidden) if forbidden else "nenhuma",
            ),
        ]
    )
