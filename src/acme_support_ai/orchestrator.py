from __future__ import annotations

from .agno_runtime import answer_with_agno
from .config import load_env_file


def answer_question(question: str) -> str:
    load_env_file()
    return answer_with_agno(question)
