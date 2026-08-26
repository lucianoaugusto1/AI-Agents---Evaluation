"""Coloca a pasta rag-evals no sys.path para os scripts rodarem da raiz do repo."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
