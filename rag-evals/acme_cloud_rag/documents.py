"""Carga do corpus e chunking.

O chunking e de tamanho fixo em caracteres. Ele nao respeita paragrafo,
titulo nem linha de tabela, entao um trecho relevante pode ficar partido em
dois chunks e nenhum dos dois responder a pergunta sozinho.
"""

from __future__ import annotations

import re
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


# Linhas de metadado do cabecalho, que descrevem o documento em vez de
# responder qualquer pergunta.
_METADATA_LINE = re.compile(r"^(versao|status)\s*:", re.IGNORECASE)

# Parentese final do titulo, onde mora o "(versao 2023 - OBSOLETA)" e o
# "(vigente desde 01/2025)".
_TITLE_QUALIFIER = re.compile(r"\s*\([^)]*\)\s*$")


def parse_document(raw: str) -> tuple[str, str, bool]:
    """Separa metadado de conteudo.

    O estado do documento (versao, vigencia) e metadado do indice, nao resposta
    ao usuario. Deixa-lo no corpo faz o modelo ler "Status: obsoleta" dentro do
    contexto e avisar sozinho que a politica esta revogada, o que esconde a
    falha que a atividade quer mostrar: o RAG entregando politica revogada com
    cara de vigente. O retriever continua sabendo, via is_obsolete; o gerador
    nao.

    O qualificador entre parenteses sai do titulo dos dois lados, obsoleto e
    vigente. Manter so o "(vigente desde 01/2025)" seria a mesma pista, ao
    contrario.
    """
    lines = raw.splitlines()
    title_line = lines[0] if lines else ""
    title = title_line.lstrip("# ").strip()

    metadata: list[str] = []
    index = 1
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        if not _METADATA_LINE.match(stripped):
            break
        metadata.append(stripped)
        index += 1

    is_obsolete = "obsolet" in " ".join([title, *metadata]).lower()
    clean_title = _TITLE_QUALIFIER.sub("", title).strip()
    content = "\n".join(lines[index:]).strip()
    body = f"# {clean_title}\n\n{content}" if content else f"# {clean_title}"
    return clean_title, body, is_obsolete


def load_documents(directory: Path | None = None) -> list[Document]:
    documents: list[Document] = []
    for path in sorted((directory or DOCUMENTS_DIR).glob("*.md")):
        title, body, is_obsolete = parse_document(path.read_text(encoding="utf-8"))
        documents.append(
            Document(
                doc_id=path.stem,
                title=title,
                body=body,
                is_obsolete=is_obsolete,
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
