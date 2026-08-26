"""Executa o golden dataset contra o RAG e imprime os scores.

Este arquivo faz parte da suite de evaluation e nao deve ser editado durante
o desafio.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from statistics import mean

from src.rag_evals import RagResult, answer_question
from src.rag_evals import config

from .judge import CaseResult, judge_case
from .observability import create_observer

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "evals" / "golden_dataset.jsonl"
TARGET = 0.85

METRICS = ["context_precision", "context_recall", "faithfulness", "answer_relevancy", "format"]


def load_cases() -> list[dict]:
    return [
        json.loads(line)
        for line in DATASET.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def summarize(results: list[CaseResult]) -> dict:
    return {
        "overall": mean(result.total for result in results),
        "metrics": {name: mean(getattr(result, name) for result in results) for name in METRICS},
    }


def current_config() -> dict:
    return {
        "chunk_size": config.CHUNK_SIZE,
        "chunk_overlap": config.CHUNK_OVERLAP,
        "filter_obsolete_documents": config.FILTER_OBSOLETE_DOCUMENTS,
        "top_k": config.TOP_K,
        "min_relevance_score": config.MIN_RELEVANCE_SCORE,
        "dedupe_by_document": config.DEDUPE_BY_DOCUMENT,
        "max_context_chars": config.MAX_CONTEXT_CHARS,
        "strict_grounding": config.STRICT_GROUNDING,
        "model": config.groq_model(),
    }


def run(trace_provider: str = "none", only: str | None = None) -> tuple[list[CaseResult], list[RagResult]]:
    observer = create_observer(trace_provider)
    cases = load_cases()
    if only:
        cases = [case for case in cases if case["id"].lower() == only.lower()]
        if not cases:
            raise SystemExit(f"caso nao encontrado: {only}")

    observer.start_run({"dataset": str(DATASET), "case_count": len(cases), "config": current_config()})
    results: list[CaseResult] = []
    rag_results: list[RagResult] = []
    for case in cases:
        rag = answer_question(case["question"])
        result = judge_case(case, rag)
        observer.log_case(case, result, rag)
        results.append(result)
        rag_results.append(rag)
    observer.end_run(summarize(results))
    return results, rag_results


def print_case_detail(result: CaseResult, rag: RagResult) -> None:
    print(f"  pergunta:    {rag.question}")
    print(f"  esperados:   {', '.join(result.expected) or '-'}")
    print(f"  recuperados: {', '.join(result.retrieved) or '-'}")
    for item in rag.retrieved:
        flag = " [OBSOLETO]" if item.chunk.is_obsolete else ""
        print(f"    {item.chunk.chunk_id:28} score={item.score:.2f}{flag}")
    print(f"  citations:   {', '.join(result.citations) or '-'}")
    print(f"  resposta:    {result.answer}")
    for name in METRICS:
        for line in result.details.get(name, []):
            if line:
                print(f"    {name}: {line}")
    for problem in result.problems:
        print(f"  - {problem}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Roda a evaluation do RAG da ACME Cloud.")
    parser.add_argument("--verbose", action="store_true", help="Mostra contexto, resposta e falhas de cada caso.")
    parser.add_argument("--case", help="Roda apenas um caso do dataset (ex.: REEMB-002).")
    parser.add_argument("--json", action="store_true", help="Escreve rag-eval-results.json.")
    parser.add_argument(
        "--trace-provider",
        choices=["none", "local", "langfuse"],
        default="none",
        help="Para onde mandar traces e scores.",
    )
    args = parser.parse_args()

    results, rag_results = run(trace_provider=args.trace_provider, only=args.case)
    summary = summarize(results)

    print("ACME Cloud RAG Evaluation")
    print("=========================")
    print(f"overall            {summary['overall']:.3f}   (meta {TARGET})")
    for name in METRICS:
        print(f"{name:18} {summary['metrics'][name]:.3f}")
    print()

    for result, rag in zip(results, rag_results):
        status = "PASS" if result.total >= TARGET else "FAIL"
        print(f"{status} {result.case_id:10} {result.total:.3f} {result.category}")
        if args.verbose:
            print_case_detail(result, rag)

    if args.json:
        payload = {
            **summary,
            "config": current_config(),
            "cases": [result.__dict__ for result in results],
        }
        (ROOT / "rag-eval-results.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print("resultados escritos em rag-eval-results.json")


if __name__ == "__main__":
    main()
