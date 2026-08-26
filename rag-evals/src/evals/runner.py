"""Runs the whole evaluation suite and renders the results."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .. import config
from ..rag import RagPipeline, TestCase, build_judge, load_dataset
from .base import MetricResult
from .context_precision import context_precision
from .context_recall import context_recall

METRICS = ["context_precision", "context_recall", "faithfulness", "answer_relevancy"]
METRIC_LABELS = {
    "context_precision": "Context Precision",
    "context_recall": "Context Recall",
    "faithfulness": "Faithfulness",
    "answer_relevancy": "Answer Relevancy",
}

console = Console()


@dataclass
class CaseResult:
    id: str
    question: str
    answer: str
    retrieved: list[str]
    expected: list[str]
    scores: dict[str, float]
    explanations: dict[str, str] = field(default_factory=dict)
    details: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class EvalReport:
    config: dict
    cases: list[CaseResult]
    averages: dict[str, float]

    def to_dict(self) -> dict:
        return {
            "config": self.config,
            "averages": self.averages,
            "cases": [asdict(c) for c in self.cases],
        }


def run_evaluation(top_k: int | None = None, strict: bool | None = None,
                   cases: list[TestCase] | None = None) -> EvalReport:
    pipeline = RagPipeline(top_k=top_k, strict=strict)
    judge = build_judge()
    cases = cases if cases is not None else load_dataset()

    results: list[CaseResult] = []
    for case in cases:
        rag = pipeline.answer(case.question)
        metrics: dict[str, MetricResult] = {
            "context_precision": context_precision(rag.contexts, case.expected_relevant_document_ids),
            "context_recall": context_recall(rag.contexts, case.expected_relevant_document_ids),
            "faithfulness": judge.faithfulness(case.question, rag.contexts, rag.answer),
            "answer_relevancy": judge.answer_relevancy(case.question, rag.answer),
        }
        results.append(
            CaseResult(
                id=case.id,
                question=case.question,
                answer=rag.answer,
                retrieved=[c.id for c in rag.contexts],
                expected=case.expected_relevant_document_ids,
                scores={name: m.score for name, m in metrics.items()},
                explanations={name: m.explanation for name, m in metrics.items()},
                details={name: m.details for name, m in metrics.items()},
            )
        )

    averages = {
        name: round(sum(r.scores[name] for r in results) / len(results), 4)
        for name in METRICS
    }
    meta = {
        "top_k": pipeline.top_k,
        "strict_context_prompt": pipeline.strict,
        "generator": pipeline.generator.name,
        "judge": judge.name,
    }
    return EvalReport(config=meta, cases=results, averages=averages)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def print_header(report: EvalReport) -> None:
    cfg = report.config
    console.print(
        Panel(
            f"TOP_K = [bold]{cfg['top_k']}[/bold]    "
            f"STRICT_CONTEXT_PROMPT = [bold]{cfg['strict_context_prompt']}[/bold]\n"
            f"generator: {cfg['generator']}    judge: {cfg['judge']}\n\n"
            "[dim]Context Precision / Context Recall are always deterministic "
            "(computed from expected_relevant_document_ids).\n"
            f"Faithfulness / Answer Relevancy come from the judge above.[/dim]",
            title="RAG evaluation",
        )
    )


def print_case(case: CaseResult, verbose: bool = True) -> None:
    console.print(f"\n[bold cyan]{case.id}[/bold cyan]  {case.question}")
    console.rule(style="dim")
    console.print("[bold]Retrieved:[/bold]")
    for line in case.details["context_precision"]:
        console.print("  " + line)
    console.print(f"  Context Precision: [bold]{case.scores['context_precision']:.2f}[/bold] "
                  f"[dim]({case.explanations['context_precision']})[/dim]")
    console.print(f"\n[bold]Context Recall:[/bold] {case.scores['context_recall']:.2f} "
                  f"[dim]({case.explanations['context_recall']})[/dim]")
    for line in case.details["context_recall"]:
        console.print("  " + line)
    console.print(f"\n[bold]Answer:[/bold] {case.answer}")
    console.print(f"[bold]Faithfulness:[/bold] {case.scores['faithfulness']:.2f} "
                  f"[dim]({case.explanations['faithfulness']})[/dim]")
    if verbose:
        for line in case.details["faithfulness"]:
            console.print("  " + line)
    console.print(f"[bold]Answer Relevancy:[/bold] {case.scores['answer_relevancy']:.2f} "
                  f"[dim]({case.explanations['answer_relevancy']})[/dim]")
    if verbose:
        for line in case.details["answer_relevancy"]:
            console.print("  " + line)


def print_summary(report: EvalReport) -> None:
    table = Table(title="Evaluation summary", header_style="bold")
    table.add_column("Test")
    for metric in METRICS:
        table.add_column(METRIC_LABELS[metric], justify="right")
    for case in report.cases:
        table.add_row(case.id, *[_colored(case.scores[m]) for m in METRICS])
    table.add_section()
    table.add_row("[bold]AVERAGE[/bold]",
                  *[f"[bold]{report.averages[m]:.2f}[/bold]" for m in METRICS])
    console.print(table)


def _colored(value: float) -> str:
    color = "green" if value >= 0.8 else "yellow" if value >= 0.5 else "red"
    return f"[{color}]{value:.2f}[/{color}]"


# ---------------------------------------------------------------------------
# Baseline handling
# ---------------------------------------------------------------------------

def save_baseline(report: EvalReport, path: Path | None = None) -> Path:
    path = path or config.BASELINE_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report.to_dict(), indent=2), encoding="utf-8")
    return path


def load_baseline(path: Path | None = None) -> dict:
    path = path or config.BASELINE_PATH
    if not path.is_file():
        raise FileNotFoundError(
            f"No baseline found at {path}. Create one first:\n"
            "    python scripts/evaluate.py --save-baseline"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def print_comparison(baseline: dict, report: EvalReport) -> None:
    before_cfg, after_cfg = baseline.get("config", {}), report.config
    console.print(
        Panel(
            f"before: TOP_K={before_cfg.get('top_k')}  "
            f"STRICT_CONTEXT_PROMPT={before_cfg.get('strict_context_prompt')}\n"
            f"after:  TOP_K={after_cfg['top_k']}  "
            f"STRICT_CONTEXT_PROMPT={after_cfg['strict_context_prompt']}",
            title="Baseline comparison",
        )
    )
    table = Table(header_style="bold")
    table.add_column("Metric")
    table.add_column("Before", justify="right")
    table.add_column("After", justify="right")
    table.add_column("Delta", justify="right")
    for metric in METRICS:
        before = float(baseline.get("averages", {}).get(metric, 0.0))
        after = report.averages[metric]
        delta = after - before
        color = "green" if delta > 0.001 else "red" if delta < -0.001 else "dim"
        table.add_row(METRIC_LABELS[metric], f"{before:.2f}", f"{after:.2f}",
                      f"[{color}]{delta:+.2f}[/{color}]")
    console.print(table)


# ---------------------------------------------------------------------------
# Thresholds / regression
# ---------------------------------------------------------------------------

def load_thresholds(path: Path | None = None) -> dict[str, float]:
    path = path or config.THRESHOLDS_PATH
    if not path.is_file():
        raise FileNotFoundError(f"Thresholds file not found: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    thresholds = data.get("thresholds")
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError(f"{path} must define a non-empty `thresholds:` mapping.")
    unknown = set(thresholds) - set(METRICS)
    if unknown:
        raise ValueError(f"Unknown metric(s) in {path}: {', '.join(sorted(unknown))}")
    return {k: float(v) for k, v in thresholds.items()}


def check_thresholds(averages: dict[str, float], thresholds: dict[str, float]) -> list[dict]:
    """Return one entry per violated threshold (empty list == suite passed)."""
    return [
        {"metric": metric, "expected": limit, "actual": averages[metric]}
        for metric, limit in thresholds.items()
        if averages.get(metric, 0.0) + 1e-9 < limit
    ]
