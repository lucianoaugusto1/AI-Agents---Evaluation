from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from src.acme_support_ai import answer_question
from .judge import CaseResult, judge_case


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "golden_dataset.jsonl"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in DATASET.read_text(encoding="utf-8").splitlines() if line.strip()]


def run() -> list[CaseResult]:
    results: list[CaseResult] = []
    for case in load_cases():
        response = answer_question(case["question"])
        results.append(judge_case(case, response))
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ACME support assistant evals.")
    parser.add_argument("--verbose", action="store_true", help="Print every response and failure reason.")
    parser.add_argument("--json", action="store_true", help="Write eval-results.json.")
    args = parser.parse_args()

    results = run()
    overall = mean(result.total for result in results)
    relevance = mean(result.relevance for result in results)
    faithfulness = mean(result.faithfulness for result in results)
    format_score = mean(result.format for result in results)
    safety = mean(result.safety for result in results)

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
            "overall": overall,
            "metrics": {
                "relevance": relevance,
                "faithfulness": faithfulness,
                "format": format_score,
                "safety": safety,
            },
            "cases": [result.__dict__ for result in results],
        }
        (ROOT / "eval-results.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
