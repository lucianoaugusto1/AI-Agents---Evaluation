"""Pipeline RAG: recuperacao -> montagem de contexto -> geracao."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from . import config
from .llm import complete
from .prompts import USER_TEMPLATE, system_prompt
from .retriever import RetrievedChunk, retrieve


@dataclass
class RagResult:
    question: str
    retrieved: list[RetrievedChunk]
    context: str
    raw_response: str
    parsed: dict[str, Any] | None
    prompt: str = ""
    model: str = ""

    @property
    def retrieved_doc_ids(self) -> list[str]:
        return [item.doc_id for item in self.retrieved]

    @property
    def retrieved_chunk_ids(self) -> list[str]:
        return [item.chunk.chunk_id for item in self.retrieved]

    @property
    def answer(self) -> str:
        if self.parsed and isinstance(self.parsed.get("answer"), str):
            return self.parsed["answer"]
        return self.raw_response

    @property
    def citations(self) -> list[str]:
        if self.parsed and isinstance(self.parsed.get("citations"), list):
            return [str(item) for item in self.parsed["citations"]]
        return []

    @property
    def refused(self) -> bool:
        return bool(self.parsed and self.parsed.get("refused") is True)


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Monta o bloco de CONTEXTO enviado ao modelo.

    O corte final e por numero de caracteres sobre o texto ja concatenado.
    """
    blocks = [
        f"[{item.chunk.chunk_id}] ({item.chunk.doc_id}) {item.chunk.text}"
        for item in chunks
    ]
    joined = "\n\n".join(blocks)
    return joined[: config.MAX_CONTEXT_CHARS]


def _parse(raw: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def answer_question(question: str) -> RagResult:
    chunks = retrieve(question, top_k=config.TOP_K)
    context = build_context(chunks)
    user = USER_TEMPLATE.format(context=context or "(nenhum documento recuperado)", question=question)
    model = config.groq_model()
    raw = complete(
        system=system_prompt(config.STRICT_GROUNDING),
        user=user,
        model=model,
        temperature=0.0,
        json_mode=True,
    )
    return RagResult(
        question=question,
        retrieved=chunks,
        context=context,
        raw_response=raw,
        parsed=_parse(raw),
        prompt=user,
        model=model,
    )
