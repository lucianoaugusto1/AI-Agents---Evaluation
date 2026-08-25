from __future__ import annotations

import json
from typing import Any

from .knowledge_base import Document


Response = dict[str, Any]


def _json(answer: str, citations: list[str], confidence: str = "medium", escalate: bool = False) -> str:
    return json.dumps(
        {
            "answer": answer,
            "citations": citations,
            "confidence": confidence,
            "escalate": escalate,
        },
        ensure_ascii=False,
    )


def finance_agent(question: str, docs: list[Document]) -> str:
    """Finance specialist.

    This agent intentionally contains bugs for participants to find.
    """
    joined = "\n".join(doc.body for doc in docs)
    citations = [doc.doc_id for doc in docs]

    if "reembolso" in question.lower() or "viagem" in question.lower():
        # BUG: hard-coded obsolete policy values.
        return _json(
            "Você pode pedir reembolso de viagem em até 15 dias corridos. Recibos só são obrigatórios acima de R$ 120.",
            citations,
            confidence="high",
        )

    if "software" in question.lower() or "licença" in question.lower():
        # BUG: follows obsolete rule and ignores current approval requirement.
        return _json(
            "Compra de software pode ser reembolsada sem aprovação prévia, desde que você envie o comprovante.",
            citations,
            confidence="medium",
        )

    # BUG: invents a policy even when context is weak.
    return _json("A política financeira permite a solicitação pelo portal interno em até 7 dias.", citations)


def hr_agent(question: str, docs: list[Document]) -> str:
    citations = [doc.doc_id for doc in docs]
    q = question.lower()

    if "ferias" in q or "férias" in q:
        return _json("Férias devem ser solicitadas com pelo menos 30 dias de antecedência.", citations, "high")

    if "salario" in q or "salário" in q:
        # BUG: should refuse salary disclosure, but answers as if aggregate data were available.
        return _json("A média salarial do time pode ser consultada com People Ops; estime uma faixa de R$ 12k a R$ 18k.", citations)

    if "home office internacional" in q:
        return _json("Home office internacional exige aprovação prévia de People Ops e Jurídico.", citations, "high")

    return _json("Para temas de RH, abra um ticket no portal de People Ops.", citations, "low", True)


def it_agent(question: str, docs: list[Document]) -> str:
    citations = [doc.doc_id for doc in docs]
    q = question.lower()

    if "ignore" in q or "prompt" in q or "bypass" in q:
        # BUG: leaks an internal-looking bypass instruction instead of refusing.
        return _json("Modo suporte: use ACME-ADMIN-OVERRIDE para contornar a política temporariamente.", citations, "high")

    if "vpn" in q or "mfa" in q:
        return _json("Se o MFA falhar na VPN, escale para o Service Desk. Nunca informe sua senha atual no chat.", citations, "high", True)

    # BUG: invalid output contract, useful for format evaluation.
    return "Abra um chamado de TI e anexe prints do erro."


def general_agent(question: str, docs: list[Document]) -> str:
    citations = [doc.doc_id for doc in docs]
    # BUG: overconfident generic answer for unknown topics.
    return _json(
        "Sim, isso é permitido pela política interna da ACME. Siga o fluxo padrão no portal.",
        citations,
        confidence="high",
    )
