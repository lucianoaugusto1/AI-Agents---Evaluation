"""Retriever lexico BM25 sobre os chunks do corpus.

BM25 e uma implementacao real, sem servico externo, para que o resultado seja
o mesmo em todas as maquinas do workshop. Os problemas de recuperacao do
desafio estao na configuracao (top-k, limiar, dedup, documento obsoleto) e no
tratamento da query, nao no algoritmo.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from .config import (
    DEDUPE_BY_DOCUMENT,
    MIN_RELEVANCE_SCORE,
    REMOVE_STOPWORDS_FROM_QUERY,
    TOP_K,
)
from .documents import Chunk, build_chunks

K1 = 1.5
B = 0.75

# Palavras muito frequentes em portugues. Sem remove-las, uma pergunta longa
# casa com quase todo documento pelo mesmo motivo errado.
STOPWORDS = {
    "a", "as", "ao", "aos", "com", "como", "da", "das", "de", "do", "dos", "e",
    "em", "essa", "esse", "eu", "meu", "minha", "na", "nas", "no", "nos", "o",
    "os", "ou", "para", "por", "posso", "qual", "quais", "quando", "quanto",
    "quantas", "quantos", "que", "se", "tem", "um", "uma", "voces",
}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-ZÀ-ÿ0-9]+", text.lower())


def normalize_query(query: str) -> list[str]:
    """Tratamento da query antes da busca.

    Com `REMOVE_STOPWORDS_FROM_QUERY` desligado a pergunta vai crua para o
    BM25 e palavras como "qual", "para" e "posso" competem com os termos que
    de fato importam.
    """
    terms = tokenize(query)
    if REMOVE_STOPWORDS_FROM_QUERY:
        return [term for term in terms if term not in STOPWORDS]
    return terms


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float

    @property
    def doc_id(self) -> str:
        return self.chunk.doc_id


class BM25Index:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks = chunks
        self.tokens = [tokenize(chunk.text) for chunk in chunks]
        self.lengths = [len(tokens) for tokens in self.tokens]
        self.avg_length = (sum(self.lengths) / len(self.lengths)) if self.lengths else 0.0
        self.doc_freq: dict[str, int] = {}
        for tokens in self.tokens:
            for term in set(tokens):
                self.doc_freq[term] = self.doc_freq.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        total = len(self.chunks)
        freq = self.doc_freq.get(term, 0)
        if freq == 0:
            return 0.0
        return math.log(1 + (total - freq + 0.5) / (freq + 0.5))

    def score(self, terms: list[str], index: int) -> float:
        tokens = self.tokens[index]
        if not tokens:
            return 0.0
        length = self.lengths[index]
        total = 0.0
        for term in terms:
            count = tokens.count(term)
            if not count:
                continue
            denominator = count + K1 * (1 - B + B * length / (self.avg_length or 1))
            total += self._idf(term) * (count * (K1 + 1)) / denominator
        return total

    def search(self, query: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
        terms = normalize_query(query)
        scored = [
            RetrievedChunk(chunk=self.chunks[index], score=self.score(terms, index))
            for index in range(len(self.chunks))
        ]
        scored = [item for item in scored if item.score > MIN_RELEVANCE_SCORE]
        scored.sort(key=lambda item: item.score, reverse=True)

        if DEDUPE_BY_DOCUMENT:
            seen: set[str] = set()
            deduped: list[RetrievedChunk] = []
            for item in scored:
                if item.doc_id in seen:
                    continue
                seen.add(item.doc_id)
                deduped.append(item)
            scored = deduped

        return scored[:top_k]


_INDEX: BM25Index | None = None


def get_index(rebuild: bool = False) -> BM25Index:
    global _INDEX
    if _INDEX is None or rebuild:
        _INDEX = BM25Index(build_chunks())
    return _INDEX


def retrieve(query: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
    return get_index().search(query, top_k=top_k)
