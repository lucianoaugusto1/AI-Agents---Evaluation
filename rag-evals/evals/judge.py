"""Avaliador do desafio de RAG.

Cinco metricas por caso:

- context_precision  deterministica  culpa o retriever (ranking)
- context_recall     deterministica  culpa o retriever (cobertura)
- faithfulness       LLM-as-a-Judge  culpa o gerador (ancoragem no contexto)
- answer_relevancy   LLM-as-a-Judge  culpa o gerador (utilidade)
- format             deterministica  contrato JSON, citacoes e recusa

Este arquivo faz parte da suite de evaluation e nao deve ser editado durante
o desafio.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from acme_cloud_rag import RagResult
from acme_cloud_rag.config import judge_model
from acme_cloud_rag.llm import complete_json

from .metrics import context_precision, context_recall

WEIGHTS = {
    "faithfulness": 0.30,
    "answer_relevancy": 0.20,
    "context_recall": 0.20,
    "context_precision": 0.15,
    "format": 0.15,
}

REQUIRED_FIELDS = {"answer", "citations", "confidence", "refused"}


@dataclass
class CaseResult:
    case_id: str
    category: str
    total: float
    context_precision: float
    context_recall: float
    faithfulness: float
    answer_relevancy: float
    format: float
    problems: list[str]
    answer: str
    citations: list[str]
    retrieved: list[str]
    expected: list[str]
    details: dict[str, Any] = field(default_factory=dict)


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", text).strip()


FAITHFULNESS_SYSTEM = """
Voce e um avaliador rigoroso de sistemas RAG.
Receba um CONTEXTO e uma RESPOSTA. Quebre a resposta em afirmacoes objetivas e
verifique, uma a uma, se cada afirmacao esta sustentada pelo contexto.
Uma afirmacao correta no mundo real, mas ausente do contexto, NAO esta
sustentada. Uma recusa explicita por falta de informacao conta como sustentada.
Responda em JSON: {"score": <0 a 1>, "unsupported": [<afirmacoes>], "reason": "<uma frase>"}
onde score = afirmacoes sustentadas / total de afirmacoes.
""".strip()

RELEVANCY_SYSTEM = """
Voce e um avaliador rigoroso de sistemas RAG.
Receba uma PERGUNTA, a RESPOSTA do sistema e os PONTOS ESPERADOS.
Avalie se a resposta responde de fato a pergunta e cobre os pontos esperados,
sem enrolacao e sem desviar do assunto.
Uma resposta evasiva ou generica recebe nota baixa mesmo que seja verdadeira.
Se o caso espera recusa, uma recusa clara por falta de informacao recebe 1.0.
Responda em JSON: {"score": <0 a 1>, "reason": "<uma frase>"}
""".strip()


def judge_faithfulness(context: str, answer: str) -> tuple[float, str, list[str]]:
    payload = complete_json(
        FAITHFULNESS_SYSTEM,
        f"CONTEXTO:\n{context or '(vazio)'}\n\nRESPOSTA:\n{answer or '(vazia)'}",
        model=judge_model(),
    )
    score = payload.get("score")
    unsupported = payload.get("unsupported") or []
    reason = str(payload.get("reason", ""))
    if not isinstance(score, (int, float)):
        return 0.0, "juiz nao retornou score valido", []
    return max(0.0, min(1.0, float(score))), reason, [str(item) for item in unsupported]


def judge_relevancy(question: str, answer: str, expected_keywords: list[str], expect_refusal: bool) -> tuple[float, str]:
    expected = ", ".join(expected_keywords) or ("recusa explicita por falta de informacao" if expect_refusal else "-")
    payload = complete_json(
        RELEVANCY_SYSTEM,
        f"PERGUNTA:\n{question}\n\nRESPOSTA:\n{answer or '(vazia)'}\n\nPONTOS ESPERADOS:\n{expected}",
        model=judge_model(),
    )
    score = payload.get("score")
    reason = str(payload.get("reason", ""))
    if not isinstance(score, (int, float)):
        return 0.0, "juiz nao retornou score valido"
    return max(0.0, min(1.0, float(score))), reason


def score_format(case: dict[str, Any], result: RagResult) -> tuple[float, list[str]]:
    """Contrato de saida: JSON valido, campos, citacoes e recusa."""
    problems: list[str] = []
    parsed = result.parsed

    if parsed is None:
        return 0.0, ["resposta nao e um objeto JSON valido"]

    missing = sorted(REQUIRED_FIELDS - set(parsed))
    if missing:
        problems.append("campos ausentes: " + ", ".join(missing))
    if not isinstance(parsed.get("citations"), list):
        problems.append("citations precisa ser uma lista")
    if not isinstance(parsed.get("refused"), bool):
        problems.append("refused precisa ser booleano")

    citations = result.citations
    known = set(result.retrieved_doc_ids)
    invalid = [item for item in citations if item.split("#")[0] not in known]
    if invalid:
        problems.append("citacoes fora do contexto recuperado: " + ", ".join(invalid))

    expected_docs = case["expected_document_ids"]
    if expected_docs and not case["expect_refusal"]:
        cited_docs = {item.split("#")[0] for item in citations}
        uncited = [doc_id for doc_id in expected_docs if doc_id not in cited_docs]
        if uncited and not result.refused:
            problems.append("nao citou os documentos que sustentam a resposta: " + ", ".join(uncited))

    if result.refused != case["expect_refusal"]:
        problems.append(f"refused deveria ser {case['expect_refusal']}")

    penalty = min(1.0, 0.25 * len(problems))
    return max(0.0, 1.0 - penalty), problems


def judge_case(case: dict[str, Any], result: RagResult) -> CaseResult:
    problems: list[str] = []
    details: dict[str, Any] = {}

    precision, precision_details = context_precision(result.retrieved_doc_ids, case["expected_document_ids"])
    recall, recall_details = context_recall(result.retrieved_doc_ids, case["expected_document_ids"])
    details["context_precision"] = precision_details
    details["context_recall"] = recall_details
    if recall < 1:
        problems.append("recuperacao incompleta: " + recall_details[-1])

    faithfulness, faith_reason, unsupported = judge_faithfulness(result.context, result.answer)
    details["faithfulness"] = [faith_reason, *(f"NAO SUSTENTADO: {item}" for item in unsupported)]

    normalized_answer = _normalize(result.answer)
    forbidden = [claim for claim in case["forbidden_claims"] if _normalize(claim) in normalized_answer]
    if forbidden:
        faithfulness = min(faithfulness, 0.0)
        problems.append("afirmacoes proibidas na resposta: " + ", ".join(forbidden))

    obsolete = [item.doc_id for item in result.retrieved if item.chunk.is_obsolete]
    if obsolete:
        problems.append("documento obsoleto no contexto: " + ", ".join(sorted(set(obsolete))))

    relevancy, relevancy_reason = judge_relevancy(
        case["question"], result.answer, case["expected_keywords"], case["expect_refusal"]
    )
    details["answer_relevancy"] = [relevancy_reason]

    format_score, format_problems = score_format(case, result)
    problems.extend(format_problems)

    scores = {
        "faithfulness": faithfulness,
        "answer_relevancy": relevancy,
        "context_recall": recall,
        "context_precision": precision,
        "format": format_score,
    }
    total = sum(WEIGHTS[name] * value for name, value in scores.items())

    return CaseResult(
        case_id=case["id"],
        category=case["category"],
        total=round(total, 3),
        context_precision=round(precision, 3),
        context_recall=round(recall, 3),
        faithfulness=round(faithfulness, 3),
        answer_relevancy=round(relevancy, 3),
        format=round(format_score, 3),
        problems=problems,
        answer=result.answer,
        citations=result.citations,
        retrieved=result.retrieved_chunk_ids,
        expected=case["expected_document_ids"],
        details=details,
    )
