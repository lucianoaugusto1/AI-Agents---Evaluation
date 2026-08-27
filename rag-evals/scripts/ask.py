"""Roda uma pergunta pelo pipeline e mostra a recuperacao e a resposta.

    uv run python rag-evals/scripts/ask.py "Qual e o prazo de reembolso?"
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from acme_cloud_rag import answer_question  # noqa: E402


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit('uso: python rag-evals/scripts/ask.py "sua pergunta"')

    question = " ".join(sys.argv[1:])
    result = answer_question(question)

    print(f"pergunta: {question}\n")
    print("chunks recuperados:")
    for item in result.retrieved:
        flag = " [OBSOLETO]" if item.chunk.is_obsolete else ""
        print(f"  {item.chunk.chunk_id:28} score={item.score:.2f}{flag}")
    print("\ncontexto enviado ao modelo:")
    print(result.context or "(vazio)")
    print("\nresposta bruta:")
    print(result.raw_response)


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        raise SystemExit(str(error))
