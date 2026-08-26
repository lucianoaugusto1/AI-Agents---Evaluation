import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evals.context_recall import context_recall
from src.retriever import RetrievedDocument


def docs(*ids: str) -> list[RetrievedDocument]:
    return [RetrievedDocument(rank=i + 1, id=d, score=0.0, text="") for i, d in enumerate(ids)]


def test_all_expected_documents_retrieved():
    assert context_recall(docs("a", "b"), ["a", "b"]).score == 1.0


def test_half_of_the_expected_documents():
    result = context_recall(docs("a", "x"), ["a", "b"])
    assert result.score == 0.5
    assert any("MISSING" in line for line in result.details)


def test_recall_ignores_ranking_order():
    assert context_recall(docs("x", "y", "a"), ["a"]).score == 1.0


def test_no_expected_documents_is_vacuously_perfect():
    assert context_recall(docs("a"), []).score == 1.0
