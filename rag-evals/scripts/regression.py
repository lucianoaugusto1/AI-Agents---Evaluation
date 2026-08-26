"""Regression suite: run the evals and enforce thresholds.

    python scripts/regression.py

Exit code 0 = PASS, 1 = FAIL. That is what makes this runnable in CI.
"""

from __future__ import annotations

import argparse

import _bootstrap  # noqa: F401
from rich.console import Console

from src.evals import runner

console = Console()


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the RAG regression suite.")
    parser.add_argument("--top-k", type=int, help="override TOP_K for this run")
    parser.add_argument("--strict-prompt", dest="strict", action="store_true", default=None,
                        help="force STRICT_CONTEXT_PROMPT=True for this run")
    args = parser.parse_args()

    thresholds = runner.load_thresholds()
    report = runner.run_evaluation(top_k=args.top_k, strict=args.strict)
    runner.print_header(report)
    runner.print_summary(report)

    failures = runner.check_thresholds(report.averages, thresholds)
    console.print()
    if not failures:
        for metric, limit in thresholds.items():
            console.print(f"  {runner.METRIC_LABELS[metric]:<18} "
                          f"{report.averages[metric]:.2f} >= {limit:.2f}  ok")
        console.print("\n[bold green]PASS[/bold green] — every threshold was met.")
        return 0

    for failure in failures:
        console.print(f"[bold red]FAILED: {runner.METRIC_LABELS[failure['metric']]}[/bold red]")
        console.print(f"  Expected: >= {failure['expected']:.2f}")
        console.print(f"  Actual:      {failure['actual']:.2f}\n")
    console.print("[bold red]FAIL[/bold red] — the suite would block this pull request.")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(2)
