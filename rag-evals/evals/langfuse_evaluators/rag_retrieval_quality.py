from dataclasses import dataclass
from typing import Any


@dataclass
class Score:
    name: str
    value: int | float | str | bool
    data_type: str
    comment: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class EvaluationResult:
    scores: list[Score]


def evaluate(ctx):
    """Context Precision e Context Recall a partir do span de recuperacao.

    Le `retrieved_doc_ids` do metadata da observacao e compara com os
    documentos rotulados no dataset. Nenhuma chamada de LLM.
    """
    expected = ctx.expected_output or {}
    metadata = getattr(ctx.observation, "metadata", None) or {}
    retrieved = metadata.get("retrieved_doc_ids") or []
    expected_docs = expected.get("expected_document_ids") or []

    if not expected_docs:
        precision, recall = 1.0, 1.0
        comment = "caso sem documento esperado"
    elif not retrieved:
        precision, recall = 0.0, 0.0
        comment = "nenhum documento recuperado"
    else:
        expected_set = set(expected_docs)
        hits = 0
        precisions = []
        for position, doc_id in enumerate(retrieved, start=1):
            if doc_id in expected_set:
                hits += 1
            precisions.append(hits / position)
        precision = sum(precisions) / len(precisions)
        found = [doc for doc in expected_docs if doc in set(retrieved)]
        recall = len(found) / len(expected_docs)
        missing = [doc for doc in expected_docs if doc not in set(retrieved)]
        comment = "faltando: " + ", ".join(missing) if missing else "recuperacao completa"

    return EvaluationResult(
        scores=[
            Score(name="context_precision", value=round(precision, 3), data_type="NUMERIC", comment=comment),
            Score(name="context_recall", value=round(recall, 3), data_type="NUMERIC", comment=comment),
        ]
    )
