"""A tiny, dependency-free BM25 retriever.

One markdown file in `data/documents/` == one document == one chunk.
Keeping chunking out of the picture makes the eval output easy to read:
a retrieved item is simply a document id such as `refund_policy`.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path

from . import config

_TOKEN = re.compile(r"[a-z0-9]+")

# Very small stopword list: enough to stop "the/of/a" from driving the ranking.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "can", "do", "does",
    "for", "from", "get", "how", "i", "if", "in", "is", "it", "long", "many",
    "me", "my", "of", "on", "or", "that", "the", "to", "was", "what", "when",
    "where", "which", "will", "with", "you", "your",
}


def tokenize(text: str) -> list[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


@dataclass(frozen=True)
class Document:
    id: str
    text: str


@dataclass(frozen=True)
class RetrievedDocument:
    rank: int  # 1-based position in the ranking
    id: str
    score: float
    text: str


def load_documents(directory: Path | None = None) -> list[Document]:
    directory = directory or config.DOCUMENTS_DIR
    if not directory.is_dir():
        raise FileNotFoundError(
            f"Knowledge base directory not found: {directory}. "
            "Run the commands from the repository root."
        )
    docs = [
        Document(id=path.stem, text=path.read_text(encoding="utf-8"))
        for path in sorted(directory.glob("*.md"))
    ]
    if not docs:
        raise ValueError(f"No .md documents found in {directory}")
    return docs


class BM25Retriever:
    """Classic BM25 ranking. No embeddings, no external service, no database."""

    def __init__(self, documents: list[Document], k1: float = 1.5, b: float = 0.75):
        self.documents = documents
        self.k1, self.b = k1, b
        self._tokens = {d.id: tokenize(d.text) for d in documents}
        self._lengths = {doc_id: len(t) for doc_id, t in self._tokens.items()}
        self._avg_len = sum(self._lengths.values()) / len(documents)

        self._df: dict[str, int] = {}
        for tokens in self._tokens.values():
            for term in set(tokens):
                self._df[term] = self._df.get(term, 0) + 1

    def _idf(self, term: str) -> float:
        n = len(self.documents)
        df = self._df.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def score(self, query_tokens: list[str], doc_id: str) -> float:
        tokens = self._tokens[doc_id]
        length = self._lengths[doc_id]
        total = 0.0
        for term in query_tokens:
            tf = tokens.count(term)
            if not tf:
                continue
            denom = tf + self.k1 * (1 - self.b + self.b * length / self._avg_len)
            total += self._idf(term) * (tf * (self.k1 + 1)) / denom
        return total

    def retrieve(self, question: str, top_k: int) -> list[RetrievedDocument]:
        query_tokens = tokenize(question)
        scored = [
            (self.score(query_tokens, d.id), d) for d in self.documents
        ]
        # Sort by score, then by id so ties are reproducible across machines.
        scored.sort(key=lambda pair: (-pair[0], pair[1].id))
        return [
            RetrievedDocument(rank=i + 1, id=doc.id, score=round(score, 4), text=doc.text)
            for i, (score, doc) in enumerate(scored[:top_k])
        ]
