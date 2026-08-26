"""Configuracao do RAG do workshop.

As constantes deste arquivo sao os parametros que os grupos podem ajustar
durante o desafio. Elas comecam com valores ruins de proposito.
"""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS_DIR = ROOT / "data" / "documents"

# --- Indexacao -------------------------------------------------------------
# Chunking de tamanho fixo, em caracteres, sem overlap.
CHUNK_SIZE = 320
CHUNK_OVERLAP = 0

# Filtrar documentos marcados como obsoletos antes de indexar.
FILTER_OBSOLETE_DOCUMENTS = False

# --- Recuperacao -----------------------------------------------------------
# Quantos chunks entram no contexto.
TOP_K = 2

# Score minimo para um chunk ser considerado util. 0.0 = aceita qualquer coisa.
MIN_RELEVANCE_SCORE = 0.0

# Impedir que dois chunks do mesmo documento ocupem o top-k.
DEDUPE_BY_DOCUMENT = False

# Limite de caracteres do contexto montado para o prompt.
MAX_CONTEXT_CHARS = 700

# --- Geracao ---------------------------------------------------------------
# Instruir o modelo a citar as fontes e a recusar quando o contexto nao cobre
# a pergunta.
STRICT_GROUNDING = False


def groq_model() -> str:
    return os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b").strip() or "qwen/qwen3.6-27b"


def judge_model() -> str:
    """Modelo usado pelo LLM-as-a-Judge. Por padrao o mesmo da geracao."""
    return os.getenv("JUDGE_MODEL", "").strip() or groq_model()
