import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag import load_dataset
from src.retriever import load_documents


def test_dataset_parses_and_has_enough_cases():
    cases = load_dataset()
    assert 8 <= len(cases) <= 12
    assert len({c.id for c in cases}) == len(cases)


def test_every_expected_document_exists():
    known = {d.id for d in load_documents()}
    for case in load_dataset():
        assert set(case.expected_relevant_document_ids) <= known


def test_dataset_covers_the_teaching_categories(tmp_path):
    categories = {c.category for c in load_dataset()}
    assert {"multi-document", "hallucination-prone", "answer-relevancy"} <= categories


def test_missing_file_raises_a_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_dataset(tmp_path / "nope.json")


def test_invalid_case_raises_a_clear_error(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"cases": [{"id": "x", "question": "q"}]}))
    with pytest.raises(ValueError):
        load_dataset(bad)


def test_unknown_document_reference_is_rejected(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"cases": [{
        "id": "x", "question": "q", "expected_answer": "a",
        "expected_relevant_document_ids": ["does_not_exist"],
    }]}))
    with pytest.raises(ValueError, match="unknown document"):
        load_dataset(bad)
