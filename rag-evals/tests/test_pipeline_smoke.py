"""End-to-end guard: the deterministic pipeline must keep the workshop's
TOP_K trade-off observable. This is the test that would catch a regression
in the teaching material itself."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evals.runner import run_evaluation
from src.generator import LocalGenerator
from src.rag import RagPipeline


def test_pipeline_answers_from_the_retrieved_context():
    result = RagPipeline(top_k=2, strict=True, generator=LocalGenerator()).answer(
        "Can I get a refund for an annual subscription after 20 days?"
    )
    assert "30 days" in result.answer
    assert result.contexts[0].id == "refund_policy"


def test_raising_top_k_improves_recall_and_costs_precision():
    small = run_evaluation(top_k=2, strict=False)
    large = run_evaluation(top_k=5, strict=False)
    assert large.averages["context_recall"] > small.averages["context_recall"]
    assert large.averages["context_precision"] < small.averages["context_precision"]


def test_strict_prompt_improves_faithfulness():
    loose = run_evaluation(top_k=2, strict=False)
    strict = run_evaluation(top_k=2, strict=True)
    assert strict.averages["faithfulness"] > loose.averages["faithfulness"]
