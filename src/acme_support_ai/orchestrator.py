from __future__ import annotations

import os
import re

from .agents import finance_agent, general_agent, hr_agent, it_agent
from .config import load_env_file
from .knowledge_base import retrieve


def route(question: str) -> str:
    """Route the question to a specialist agent.

    The router is intentionally simplistic. Participants can improve it.
    """
    q = question.lower()
    terms = set(re.findall(r"[a-zA-ZÀ-ÿ0-9]+", q))
    if terms & {"reembolso", "viagem", "nota", "fiscal", "recibo", "software"}:
        return "finance"
    if terms & {"ferias", "férias", "salario", "salário"} or "home office" in q:
        return "hr"
    if terms & {"vpn", "mfa", "senha", "prompt", "bypass", "monitor", "ti"}:
        return "it"
    return "general"


def answer_question(question: str) -> str:
    load_env_file()
    if os.getenv("ACME_AGENT_RUNTIME", "scripted").lower() == "agno":
        from .agno_runtime import answer_with_agno

        return answer_with_agno(question)

    docs = retrieve(question)
    selected = route(question)

    if selected == "finance":
        return finance_agent(question, docs)
    if selected == "hr":
        return hr_agent(question, docs)
    if selected == "it":
        return it_agent(question, docs)
    return general_agent(question, docs)
