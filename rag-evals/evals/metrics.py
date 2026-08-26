"""Metricas deterministicas de recuperacao.

Nenhuma delas chama LLM: elas comparam o que o retriever trouxe com os
documentos rotulados no golden dataset. Sao as metricas que acusam o
retriever, nao o gerador.
"""

from __future__ import annotations


def context_precision(retrieved_doc_ids: list[str], expected_doc_ids: list[str]) -> tuple[float, list[str]]:
    """Average Precision sobre os documentos recuperados.

        AP = (1 / |esperados|) * soma de P@i nas posicoes i que sao relevantes

    A formula e sensivel a ordem: um documento relevante em primeiro lugar
    vale 1.0, o mesmo documento em terceiro vale 0.33. Trazer mais chunks nao
    derruba a nota por si so, mas empurrar o documento certo para baixo do
    ruido derruba.
    """
    if not expected_doc_ids:
        # Casos fora de escopo nao tem documento relevante para ranquear.
        return 1.0, ["caso sem documento esperado"]
    if not retrieved_doc_ids:
        return 0.0, ["nenhum chunk recuperado"]

    expected = set(expected_doc_ids)
    seen: set[str] = set()
    hits = 0
    total = 0.0
    details: list[str] = []
    for position, doc_id in enumerate(retrieved_doc_ids, start=1):
        relevant = doc_id in expected
        first_time = relevant and doc_id not in seen
        if relevant:
            hits += 1
            seen.add(doc_id)
        precision_at_i = hits / position
        if first_time:
            total += precision_at_i
        details.append(
            f"{position}. {doc_id:26} {'relevante ' if relevant else 'irrelevante'} P@{position}={precision_at_i:.2f}"
        )
    return total / len(expected_doc_ids), details


def context_recall(retrieved_doc_ids: list[str], expected_doc_ids: list[str]) -> tuple[float, list[str]]:
    """Fracao dos documentos esperados que o retriever trouxe."""
    if not expected_doc_ids:
        return 1.0, ["caso sem documento esperado"]
    retrieved = set(retrieved_doc_ids)
    found = [doc_id for doc_id in expected_doc_ids if doc_id in retrieved]
    missing = [doc_id for doc_id in expected_doc_ids if doc_id not in retrieved]
    details = [
        "esperados: " + ", ".join(expected_doc_ids),
        "recuperados: " + (", ".join(retrieved_doc_ids) or "-"),
    ]
    if missing:
        details.append("FALTANDO: " + ", ".join(missing))
    return len(found) / len(expected_doc_ids), details
