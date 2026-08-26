"""Workshop configuration.

Only a handful of knobs live here on purpose: these are the ones the
participant is asked to change during the exercise.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# EXPERIMENT 1 — how many documents the retriever returns.
# Try 2, then 5, and compare Context Recall against Context Precision.
# ---------------------------------------------------------------------------
TOP_K = 2

# ---------------------------------------------------------------------------
# EXPERIMENT 2 — how the generator is allowed to answer.
# False -> chatty generator that pads the answer and guesses when the context
#          is not enough (hurts Faithfulness and Answer Relevancy).
# True  -> answers strictly from the retrieved context and says
#          "not enough information" when the context does not cover the question.
# ---------------------------------------------------------------------------
STRICT_CONTEXT_PROMPT = False

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DOCUMENTS_DIR = ROOT / "data" / "documents"
DATASET_PATH = ROOT / "data" / "eval_dataset.json"
THRESHOLDS_PATH = ROOT / "thresholds.yaml"
BASELINE_PATH = ROOT / "baselines" / "baseline.json"


def eval_mode() -> str:
    """`local`, `openai` or `auto` (default). Read from the environment/.env."""
    return os.getenv("EVAL_MODE", "auto").strip().lower() or "auto"


def openai_api_key() -> str | None:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    return key or None


def eval_model() -> str:
    return os.getenv("EVAL_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"
