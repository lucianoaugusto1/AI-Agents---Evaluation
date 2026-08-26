"""Atalho para rodar a evaluation de qualquer diretorio.

    uv run python rag-evals/scripts/run_eval.py --verbose
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.run_eval import main  # noqa: E402

if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error))
