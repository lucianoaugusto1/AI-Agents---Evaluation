"""Tests always run in deterministic local mode, even if a developer has an
OPENAI_API_KEY exported."""

import os

os.environ["EVAL_MODE"] = "local"
