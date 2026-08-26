"""Cliente Groq compartilhado pela geracao e pelo LLM-as-a-Judge."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parent


def load_env_file(path: Path | None = None) -> None:
    """Le KEY=VALUE de um .env sem sobrescrever variaveis ja definidas.

    Procura primeiro o .env da raiz do repositorio, que e o mesmo usado pela
    atividade de agentes.
    """
    candidates = [path] if path else [REPO_ROOT / ".env", ROOT / ".env"]
    for candidate in candidates:
        if candidate is None or not candidate.exists():
            continue
        for raw_line in candidate.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return


_CLIENT = None


def get_client():
    global _CLIENT
    if _CLIENT is None:
        load_env_file()
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY nao configurada. Copie .env.example para .env na raiz do "
                "repositorio e preencha a chave da Groq."
            )
        from groq import Groq

        _CLIENT = Groq(api_key=api_key)
    return _CLIENT


def complete(
    system: str,
    user: str,
    model: str,
    temperature: float = 0.0,
    json_mode: bool = False,
) -> str:
    kwargs = {
        "model": model,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    response = get_client().chat.completions.create(**kwargs)
    return (response.choices[0].message.content or "").strip()


def complete_json(system: str, user: str, model: str) -> dict:
    """Chamada usada pelos juizes, onde a saida precisa ser um objeto JSON."""
    raw = complete(system, user, model=model, temperature=0.0, json_mode=True)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
