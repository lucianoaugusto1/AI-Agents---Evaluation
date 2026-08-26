"""Cliente Groq compartilhado pela geracao e pelo LLM-as-a-Judge."""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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
    reasoning_effort: str | None = None,
) -> str:
    """Uma chamada de chat completion.

    Modelos com raciocinio longo as vezes estouram o orcamento de tokens antes
    de fechar o JSON, e a Groq responde 400 com `json_validate_failed`. Quando
    isso acontece a chamada e repetida com o raciocinio desligado.
    """
    def _call(effort: str | None) -> str:
        kwargs: dict = {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        if effort is not None:
            kwargs["reasoning_effort"] = effort
        response = get_client().chat.completions.create(**kwargs)
        return (response.choices[0].message.content or "").strip()

    try:
        return _call(reasoning_effort)
    except Exception:
        if reasoning_effort == "none":
            raise
        try:
            return _call("none")
        except Exception:
            return ""


def complete_json(system: str, user: str, model: str) -> dict:
    """Chamada usada pelos juizes, onde a saida precisa ser um objeto JSON.

    O juiz roda sem raciocinio estendido: a nota fica mais estavel entre
    execucoes e a suite inteira cabe no tempo do workshop.
    """
    raw = complete(system, user, model=model, temperature=0.0, json_mode=True, reasoning_effort="none")
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}
