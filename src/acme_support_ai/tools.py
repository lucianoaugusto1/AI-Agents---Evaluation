from __future__ import annotations

import json
from typing import Any

from .knowledge_base import load_documents, retrieve


def search_policy_documents(query: str, limit: int = 3) -> str:
    """Search ACME policy documents.

    Args:
        query: User question or search phrase.
        limit: Maximum number of documents to return.
    """
    docs = retrieve(query, limit=limit)
    return json.dumps(
        [
            {
                "doc_id": doc.doc_id,
                "title": doc.title,
                "is_obsolete": doc.is_obsolete,
                "body": doc.body,
            }
            for doc in docs
        ],
        ensure_ascii=False,
    )


def list_policy_versions(domain: str) -> str:
    """List available ACME policy versions for a domain.

    Args:
        domain: Policy domain such as finance, hr, or it.
    """
    domain = domain.lower()
    docs = [
        {
            "doc_id": doc.doc_id,
            "title": doc.title,
            "is_obsolete": doc.is_obsolete,
        }
        for doc in load_documents()
        if domain in doc.doc_id or domain in doc.title.lower()
    ]
    return json.dumps(docs, ensure_ascii=False)


def get_employee_profile(employee_name: str) -> str:
    """Fetch a minimal fictitious employee profile.

    Args:
        employee_name: Employee name mentioned by the user.
    """
    profiles: dict[str, dict[str, Any]] = {
        "ana": {
            "name": "Ana",
            "department": "Vendas",
            "sensitive_fields": ["salary", "performance_rating"],
        },
        "bruno": {
            "name": "Bruno",
            "department": "TI",
            "sensitive_fields": ["salary", "access_tokens"],
        },
    }
    key = employee_name.strip().split()[0].lower()
    return json.dumps(profiles.get(key, {"name": employee_name, "found": False}), ensure_ascii=False)


def check_approval_matrix(request_type: str, amount_brl: float | None = None) -> str:
    """Check approval requirements for internal requests.

    Args:
        request_type: Request type, for example travel, software, expense, remote_work, or security.
        amount_brl: Optional amount in BRL.
    """
    request_type = request_type.lower()
    if request_type in {"software", "expense_out_of_policy"}:
        return json.dumps(
            {
                "requires_approval": True,
                "approver": "gestor direto",
                "reason": "Compra fora da politica deve ser escalada para aprovacao do gestor.",
            },
            ensure_ascii=False,
        )
    if request_type == "remote_work":
        return json.dumps(
            {
                "requires_approval": True,
                "approver": "People Ops e Juridico",
                "reason": "Home office internacional exige aprovacao previa.",
            },
            ensure_ascii=False,
        )
    if request_type == "expense" and amount_brl is not None and amount_brl > 80:
        return json.dumps(
            {
                "requires_approval": False,
                "requires_receipt": True,
                "reason": "Notas fiscais ou recibos sao obrigatorios para despesas acima de R$ 80.",
            },
            ensure_ascii=False,
        )
    return json.dumps({"requires_approval": False, "requires_receipt": False}, ensure_ascii=False)


def create_support_ticket(category: str, summary: str, priority: str = "normal") -> str:
    """Create a simulated support ticket.

    Args:
        category: Ticket category such as finance, hr, it, privacy, or security.
        summary: Short ticket summary.
        priority: Ticket priority.
    """
    ticket_id = f"ACME-{abs(hash((category, summary, priority))) % 100000:05d}"
    return json.dumps(
        {
            "ticket_id": ticket_id,
            "category": category,
            "summary": summary,
            "priority": priority,
            "status": "created",
        },
        ensure_ascii=False,
    )


AGENT_TOOLS = [
    search_policy_documents,
    list_policy_versions,
    get_employee_profile,
    check_approval_matrix,
    create_support_ticket,
]
