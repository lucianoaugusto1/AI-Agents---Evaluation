from dataclasses import dataclass
from typing import Any
import json


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


def evaluate(ctx):
    output = ctx.observation.output
    raw = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)
    problems = []
    parsed = None

    try:
        parsed = json.loads(raw)
    except Exception:
        problems.append("response is not valid JSON")

    if isinstance(parsed, dict):
        required = {"answer", "citations", "confidence", "escalate"}
        missing = sorted(required - set(parsed))
        if missing:
            problems.append("missing fields: " + ", ".join(missing))
        if not isinstance(parsed.get("citations"), list):
            problems.append("citations must be a list")
        if not isinstance(parsed.get("escalate"), bool):
            problems.append("escalate must be boolean")
    elif parsed is not None:
        problems.append("response JSON must be an object")

    passed = len(problems) == 0
    return EvaluationResult(
        scores=[
            Score(
                name="json_contract",
                value=passed,
                data_type="BOOLEAN",
                comment="OK" if passed else "; ".join(problems),
                metadata={"problems": problems},
            ),
            Score(
                name="format",
                value=1.0 if passed else 0.0,
                data_type="NUMERIC",
                comment="Deterministic JSON contract score.",
            ),
        ]
    )
