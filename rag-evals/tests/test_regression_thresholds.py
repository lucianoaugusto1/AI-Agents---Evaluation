import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evals.runner import METRICS, check_thresholds, load_thresholds

PASSING = {"context_precision": 0.9, "context_recall": 0.9,
           "faithfulness": 0.9, "answer_relevancy": 0.9}


def test_thresholds_file_defines_every_metric():
    thresholds = load_thresholds()
    assert set(thresholds) == set(METRICS)


def test_suite_passes_when_every_metric_is_above_the_threshold():
    assert check_thresholds(PASSING, load_thresholds()) == []


def test_failure_reports_metric_expected_and_actual():
    averages = dict(PASSING, context_precision=0.64)
    failures = check_thresholds(averages, {"context_precision": 0.70})
    assert failures == [{"metric": "context_precision", "expected": 0.70, "actual": 0.64}]


def test_score_exactly_on_the_threshold_passes():
    assert check_thresholds({"faithfulness": 0.85}, {"faithfulness": 0.85}) == []


def test_unknown_metric_in_thresholds_file_is_rejected(tmp_path):
    bad = tmp_path / "thresholds.yaml"
    bad.write_text("thresholds:\n  made_up_metric: 0.5\n")
    with pytest.raises(ValueError):
        load_thresholds(bad)
