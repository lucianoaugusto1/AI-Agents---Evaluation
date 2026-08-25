from __future__ import annotations

from src.acme_support_ai import answer_question
from .judge import judge_case
from .run_eval import load_cases


def overall_score(input: dict, output: str, expected: dict | None = None) -> float:
    case = expected or input
    return judge_case(case, output).total


def faithfulness_score(input: dict, output: str, expected: dict | None = None) -> float:
    case = expected or input
    return judge_case(case, output).faithfulness


def main() -> None:
    from braintrust import Eval

    cases = load_cases()
    Eval(
        "ACME Agents Eval Challenge",
        data=lambda: [{"input": case, "expected": case} for case in cases],
        task=lambda input: answer_question(input["question"]),
        scores=[overall_score, faithfulness_score],
        metadata={"system": "acme-support-ai", "challenge": "evaluation-workshop"},
    )


if __name__ == "__main__":
    main()
