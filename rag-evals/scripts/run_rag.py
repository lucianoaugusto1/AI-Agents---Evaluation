"""Run the RAG pipeline on one question and show every step.

    python scripts/run_rag.py
    python scripts/run_rag.py "What is the API rate limit for the Pro plan?"
"""

from __future__ import annotations

import sys

import _bootstrap  # noqa: F401
from rich.console import Console
from rich.panel import Panel

from src import config
from src.rag import RagPipeline

DEFAULT_QUESTION = "Can I get a refund for an annual subscription after 20 days?"
console = Console()


def main() -> int:
    question = " ".join(sys.argv[1:]).strip() or DEFAULT_QUESTION
    pipeline = RagPipeline()

    console.print(Panel(
        f"TOP_K = [bold]{pipeline.top_k}[/bold]    "
        f"STRICT_CONTEXT_PROMPT = [bold]{pipeline.strict}[/bold]    "
        f"generator = {pipeline.generator.name}",
        title="Configuration (src/config.py)",
    ))

    result = pipeline.answer(question)
    console.print(f"\n[bold]Question:[/bold] {question}")
    console.print("\n[bold]Retrieved context (top-k):[/bold]")
    for doc in result.contexts:
        console.print(f"  {doc.rank}. [cyan]{doc.id}[/cyan]  (bm25 score {doc.score})")
    console.print(f"\n[bold]Answer:[/bold]\n{result.answer}\n")
    console.print("[dim]Nothing here is scored yet. Run "
                  "`python scripts/evaluate.py` to measure this pipeline.[/dim]")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise SystemExit(2)
