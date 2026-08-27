from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean
import time
from typing import Any

from src.acme_support_ai import answer_question
from src.acme_support_ai.config import load_env_file
from .judge import CaseResult, judge_case
from .observability import create_observer


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "golden_dataset.jsonl"
LANGFUSE_DATASET_NAME = "acme-agents-golden-dataset"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(results: list[CaseResult]) -> dict:
    return {
        "overall": mean(result.total for result in results),
        "metrics": {
            "relevance": mean(result.relevance for result in results),
            "faithfulness": mean(result.faithfulness for result in results),
            "format": mean(result.format for result in results),
            "safety": mean(result.safety for result in results),
        },
    }


def _raw_output(output: Any) -> str:
    if isinstance(output, str):
        return output
    return json.dumps(output, ensure_ascii=False, default=str)


def _answer_or_runtime_error(question: str) -> str:
    try:
        return answer_question(question)
    except Exception as exc:
        return f"__ACME_RUNTIME_ERROR__: {type(exc).__name__}: {exc}"


def _case_from_parts(
    *,
    input_data: Any,
    expected_output: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
) -> dict[str, Any]:
    expected = expected_output or {}
    meta = metadata or {}
    question = input_data.get("question", "") if isinstance(input_data, dict) else str(input_data)
    return {
        "id": meta.get("case_id", "unknown"),
        "question": question,
        "expected_keywords": expected.get("expected_keywords", []),
        "required_citations": expected.get("required_citations", []),
        "forbidden_claims": expected.get("forbidden_claims", []),
        "expect_json": expected.get("expect_json", True),
        "expect_escalate": expected.get("expect_escalate"),
        "category": meta.get("category", "unknown"),
    }


def _case_from_langfuse_item(item: Any) -> dict[str, Any]:
    return _case_from_parts(
        input_data=getattr(item, "input", {}),
        expected_output=getattr(item, "expected_output", None),
        metadata=getattr(item, "metadata", None),
    )


def _judge_from_experiment(
    *,
    input: Any,
    output: Any,
    expected_output: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
) -> CaseResult:
    case = _case_from_parts(input_data=input, expected_output=expected_output, metadata=metadata)
    return judge_case(case, _raw_output(output))


def run_langfuse_experiment(run_name: str | None = None) -> list[CaseResult]:
    load_env_file()
    from langfuse import Evaluation, get_client

    langfuse = get_client()
    dataset = langfuse.get_dataset(LANGFUSE_DATASET_NAME)

    def task(*, item, **kwargs):
        input_data = getattr(item, "input", {})
        question = input_data.get("question", "") if isinstance(input_data, dict) else str(input_data)
        return _answer_or_runtime_error(question)

    def relevance_evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
        result = _judge_from_experiment(
            input=input,
            output=output,
            expected_output=expected_output,
            metadata=metadata,
        )
        return Evaluation(
            name="relevance",
            value=result.relevance,
            comment="Expected content coverage.",
            metadata={"problems": result.problems},
        )

    def faithfulness_evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
        result = _judge_from_experiment(
            input=input,
            output=output,
            expected_output=expected_output,
            metadata=metadata,
        )
        return Evaluation(
            name="faithfulness",
            value=result.faithfulness,
            comment="Citation and forbidden-claim check.",
            metadata={"problems": result.problems},
        )

    def format_evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
        result = _judge_from_experiment(
            input=input,
            output=output,
            expected_output=expected_output,
            metadata=metadata,
        )
        return Evaluation(
            name="format",
            value=result.format,
            comment="JSON output contract check.",
            metadata={"problems": result.problems},
        )

    def safety_evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
        result = _judge_from_experiment(
            input=input,
            output=output,
            expected_output=expected_output,
            metadata=metadata,
        )
        return Evaluation(
            name="safety",
            value=result.safety,
            comment="Forbidden claim and escalation check.",
            metadata={"problems": result.problems},
        )

    def overall_evaluator(*, input, output, expected_output=None, metadata=None, **kwargs):
        result = _judge_from_experiment(
            input=input,
            output=output,
            expected_output=expected_output,
            metadata=metadata,
        )
        return Evaluation(
            name="overall",
            value=result.total,
            comment="Weighted deterministic score.",
            metadata={"problems": result.problems},
        )

    def run_average(*, item_results, **kwargs):
        values = [
            evaluation.value
            for item_result in item_results
            for evaluation in item_result.evaluations
            if evaluation.name == "overall" and isinstance(evaluation.value, int | float)
        ]
        return Evaluation(
            name="overall_avg",
            value=round(mean(values), 3) if values else None,
            comment="Average overall score for the dataset run.",
        )

    experiment_result = dataset.run_experiment(
        name="ACME Agents Evaluation",
        run_name=run_name or time.strftime("acme-agents-%Y%m%d-%H%M%S"),
        description="Workshop evaluation run for ACME Support AI agents.",
        task=task,
        evaluators=[
            overall_evaluator,
            relevance_evaluator,
            faithfulness_evaluator,
            format_evaluator,
            safety_evaluator,
        ],
        run_evaluators=[run_average],
        max_concurrency=1,
        metadata={"workshop": "acme-agents-eval-challenge"},
    )

    if getattr(experiment_result, "dataset_run_url", None):
        print(f"langfuse dataset run: {experiment_result.dataset_run_url}")

    results = []
    for item_result in experiment_result.item_results:
        case = _case_from_langfuse_item(item_result.item)
        results.append(judge_case(case, _raw_output(item_result.output)))
    return results


def run(trace_provider: str = "none", run_name: str | None = None) -> list[CaseResult]:
    if trace_provider == "langfuse":
        return run_langfuse_experiment(run_name=run_name)

    observer = create_observer(trace_provider)
    cases = load_cases()
    results: list[CaseResult] = []
    observer.start_run({"dataset": str(DATASET), "case_count": len(cases)})
    for case in cases:
        response = _answer_or_runtime_error(case["question"])
        result = judge_case(case, response)
        results.append(result)
        observer.log_case(case, result)
    observer.end_run(summarize(results))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ACME support assistant evals.")
    parser.add_argument("--verbose", action="store_true", help="Print every response and failure reason.")
    parser.add_argument("--json", action="store_true", help="Write eval-results.json.")
    parser.add_argument(
        "--trace-provider",
        choices=["none", "local", "langfuse"],
        default="none",
        help="Send evaluation traces and scores to a provider.",
    )
    parser.add_argument("--run-name", help="Optional Langfuse dataset run name.")
    args = parser.parse_args()

    results = run(trace_provider=args.trace_provider, run_name=args.run_name)
    summary = summarize(results)
    overall = summary["overall"]
    relevance = summary["metrics"]["relevance"]
    faithfulness = summary["metrics"]["faithfulness"]
    format_score = summary["metrics"]["format"]
    safety = summary["metrics"]["safety"]

    print("ACME Agents Evaluation")
    print("======================")
    print(f"overall      {overall:.3f}")
    print(f"relevance    {relevance:.3f}")
    print(f"faithfulness {faithfulness:.3f}")
    print(f"format       {format_score:.3f}")
    print(f"safety       {safety:.3f}")
    print()

    for result in results:
      status = "PASS" if result.total >= 0.85 else "FAIL"
      print(f"{status} {result.case_id:7} {result.total:.3f} {result.category}")
      if args.verbose and result.problems:
          for problem in result.problems:
              print(f"  - {problem}")
          print(f"  response: {result.response}")

    if args.json:
        payload = {
            **summary,
            "cases": [result.__dict__ for result in results],
        }
        (ROOT / "eval-results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
