"""Run the evaluation dataset against the RAG pipeline.

    python scripts/evaluate.py                     # scores + summary table
    python scripts/evaluate.py --save-baseline     # store the current scores
    python scripts/evaluate.py --compare-baseline  # diff against the baseline
    python scripts/evaluate.py --case refund-002   # focus on a single case
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from rich.console import Console

from src.evals import runner

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the RAG evaluation suite.")
    parser.add_argument("--save-baseline", action="store_true",
                        help="save the current averages as the baseline")
    parser.add_argument("--compare-baseline", action="store_true",
                        help="compare the current run against the saved baseline")
    parser.add_argument("--case", help="only evaluate this test case id")
    parser.add_argument("--quiet", action="store_true",
                        help="only print the summary table")
    parser.add_argument("--top-k", type=int, help="override TOP_K for this run")
    args = parser.parse_args()

    cases = runner.load_dataset()
    if args.case:
        cases = [c for c in cases if c.id == args.case]
        if not cases:
            console.print(f"[red]Error:[/red] no test case with id '{args.case}'.")
            return 2

    report = runner.run_evaluation(top_k=args.top_k, cases=cases)
    runner.print_header(report)
    if not args.quiet:
        for case in report.cases:
            runner.print_case(case)
        console.print()
    runner.print_summary(report)

    if args.compare_baseline:
        baseline = runner.load_baseline()
        console.print()
        runner.print_comparison(baseline, report)

    if args.save_baseline:
        path = runner.save_baseline(report)
        console.print(f"\n[green]Baseline saved to {path}[/green]")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(2)
