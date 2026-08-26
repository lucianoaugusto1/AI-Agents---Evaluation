"""Carga do corpus e chunking.

O chunking e de tamanho fixo em caracteres. Ele nao respeita paragrafo,
titulo nem linha de tabela, entao um trecho relevante pode ficar partido em
dois chunks e nenhum dos dois responder a pergunta sozinho.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .config import CHUNK_OVERLAP, CHUNK_SIZE, DOCUMENTS_DIR, FILTER_OBSOLETE_DOCUMENTS


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    body: str
    is_obsolete: bool


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    doc_id: str
    doc_title: str
    text: str
    is_obsolete: bool


def load_documents(directory: Path | None = None) -> list[Document]:
    documents: list[Document] = []
    for path in sorted((directory or DOCUMENTS_DIR).glob("*.md")):
        body = path.read_text(encoding="utf-8")
        title = body.splitlines()[0].lstrip("# ").strip()
        header = body[:400].lower()
        documents.append(
            Document(
                doc_id=path.stem,
                title=title,
                body=body,
                is_obsolete="obsolet" in header,
            )
        )
    return documents


def split_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if size <= 0:
        raise ValueError("CHUNK_SIZE precisa ser maior que zero")
    step = max(1, size - max(0, overlap))
    pieces = [text[start : start + size].strip() for start in range(0, len(text), step)]
    return [piece for piece in pieces if piece]


def build_chunks(documents: list[Document] | None = None) -> list[Chunk]:
    docs = documents if documents is not None else load_documents()
    if FILTER_OBSOLETE_DOCUMENTS:
        docs = [doc for doc in docs if not doc.is_obsolete]

    chunks: list[Chunk] = []
    for doc in docs:
        for index, piece in enumerate(split_text(doc.body)):
            chunks.append(
                Chunk(
                    chunk_id=f"{doc.doc_id}#{index}",
                    doc_id=doc.doc_id,
                    doc_title=doc.title,
                    text=piece,
                    is_obsolete=doc.is_obsolete,
                )
            )
    return chunks
