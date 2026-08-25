from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


POLICY_DIR = Path(__file__).parent / "policies"


@dataclass(frozen=True)
class Document:
    doc_id: str
    title: str
    body: str
    is_obsolete: bool = False


def load_documents() -> list[Document]:
    docs: list[Document] = []
    for path in sorted(POLICY_DIR.glob("*.md")):
        body = path.read_text(encoding="utf-8")
        title = body.splitlines()[0].lstrip("# ").strip()
        docs.append(
            Document(
                doc_id=path.stem,
                title=title,
                body=body,
                is_obsolete="obsoleto" in body.lower() or "antiga" in title.lower(),
            )
        )
    return docs


def retrieve(query: str, limit: int = 2) -> list[Document]:
    """Naive retriever with intentional flaws for the workshop.

    Known issues:
    - It does not filter obsolete documents.
    - It overweights generic word overlap.
    - It has no threshold for "no useful context found".
    """
    words = set(re.findall(r"[a-zA-ZÀ-ÿ0-9]+", query.lower()))
    scored: list[tuple[int, Document]] = []
    for doc in load_documents():
        doc_words = set(re.findall(r"[a-zA-ZÀ-ÿ0-9]+", doc.body.lower()))
        score = len(words & doc_words)
        if score:
            scored.append((score, doc))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:limit]]
