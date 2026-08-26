import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evals.context_precision import context_precision
from src.retriever import RetrievedDocument


def docs(*ids: str) -> list[RetrievedDocument]:
    return [RetrievedDocument(rank=i + 1, id=d, score=0.0, text="") for i, d in enumerate(ids)]


def test_single_relevant_document_first_beats_last():
    first = context_precision(docs("refund_policy", "a", "b"), ["refund_policy"]).score
    last = context_precision(docs("a", "b", "refund_policy"), ["refund_policy"]).score
    assert first > last


def test_perfect_ranking_scores_one():
    result = context_precision(docs("a", "b"), ["a", "b"])
    assert result.score == 1.0


def test_mean_precision_at_k_formula():
    # ranks: irrelevant, relevant -> (0/1 + 1/2) / 2 = 0.25
    assert context_precision(docs("x", "a"), ["a"]).score == 0.25


def test_more_noise_lowers_the_score():
    small = context_precision(docs("a", "x"), ["a"]).score
    large = context_precision(docs("a", "x", "y", "z", "w"), ["a"]).score
    assert large < small


def test_no_retrieved_documents():
    assert context_precision([], ["a"]).score == 0.0
