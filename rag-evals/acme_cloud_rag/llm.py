"""Cliente Groq compartilhado pela geracao e pelo LLM-as-a-Judge."""

from __future__ import annotations

import atexit
import json
import os
import sys
import time
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


# Quantas vezes uma chamada recusada por rate limit e repetida antes de
# desistir. A free tier da Groq limita tokens por minuto, e a suite completa
# faz tres chamadas por caso do dataset: sem repeticao a run morre no meio.
MAX_RATE_LIMIT_RETRIES = 6

# Espera minima entre tentativas quando o provedor nao diz quanto esperar.
# A Groq costuma pedir menos de um segundo, entao comecar em 2s desperdicava
# tempo de parede: quase toda a espera da suite era backoff excessivo.
RATE_LIMIT_BASE_DELAY = 0.5
RATE_LIMIT_MAX_DELAY = 30.0

# Teto de espera acumulada por execucao, em segundos. Sem ele uma unica chamada
# pode dormir MAX_RATE_LIMIT_RETRIES * RATE_LIMIT_MAX_DELAY, e a suite inteira
# rasteja em silencio por muitos minutos quando a cota esta saturada. Falhar
# rapido com uma mensagem clara e melhor que um terminal parado sem explicacao.
RATE_LIMIT_TOTAL_WAIT_BUDGET = float(os.getenv("RAG_RATE_LIMIT_BUDGET", "120"))

# Estatisticas de rate limit da execucao. Ligue RAG_DEBUG_RATE_LIMIT=1 para ver
# quanto da run foi espera, e nao trabalho.
STATS = {"calls": 0, "retries": 0, "wait_seconds": 0.0, "warned": False}


class RateLimitExhausted(RuntimeError):
    """Rate limit que sobreviveu a todas as repeticoes.

    Vira erro visivel de proposito. Devolver texto vazio aqui faria o juiz
    pontuar zero e a suite reportar uma nota que nao mede o RAG, e sim a cota
    do provedor.
    """


def _warn_rate_limit(model: str, delay: float) -> None:
    """Avisa que a pausa e cota do provedor, nao lentidao do RAG.

    Sem isso o participante ve o terminal parado e nao tem como saber que o
    problema esta do lado da Groq.
    """
    if not STATS["warned"]:
        STATS["warned"] = True
        print(
            f"\n[rate limit] A Groq recusou uma chamada no modelo {model} por "
            "limite de tokens por minuto.\n"
            "[rate limit] Isso e cota do provedor, nao lentidao do RAG. "
            "A execucao continua, esperando e repetindo.\n",
            file=sys.stderr,
            flush=True,
        )
    print(
        f"[rate limit] esperando {delay:.1f}s "
        f"(acumulado {STATS['wait_seconds'] + delay:.0f}s de "
        f"{RATE_LIMIT_TOTAL_WAIT_BUDGET:.0f}s)",
        file=sys.stderr,
        flush=True,
    )


def _rate_limit_help(model: str, error: Exception) -> str:
    return (
        f"RATE LIMIT DA GROQ - a execucao parou por cota, nao por erro do RAG.\n\n"
        f"Esperei {STATS['wait_seconds']:.0f}s no total e as chamadas continuam "
        f"sendo recusadas no modelo {model}.\n\n"
        "O limite e por organizacao e por modelo (tokens por minuto), entao gerar "
        "uma chave nova na mesma conta nao ajuda: a cota e a mesma.\n\n"
        "O que fazer:\n"
        "  - Espere alguns minutos sem rodar nada e tente de novo.\n"
        "  - Itere com --case CASO em vez da suite completa.\n"
        "  - Use um JUDGE_MODEL diferente do GROQ_MODEL: a cota e por modelo, "
        "entao juiz e gerador separados dividem o consumo em dois buckets.\n"
        "  - Para esperar mais antes de desistir: RAG_RATE_LIMIT_BUDGET=300\n\n"
        f"Mensagem do provedor: {error}"
    )


def _is_rate_limit(error: Exception) -> bool:
    if type(error).__name__ == "RateLimitError":
        return True
    return getattr(getattr(error, "response", None), "status_code", None) == 429


def _retry_delay(error: Exception, attempt: int) -> float:
    """Quanto esperar antes da proxima tentativa.

    A Groq responde com o header `retry-after` e costuma pedir menos de um
    segundo. Quando o header nao vem, cai no backoff exponencial.
    """
    headers = getattr(getattr(error, "response", None), "headers", None) or {}
    raw = headers.get("retry-after") or headers.get("Retry-After")
    if raw:
        try:
            return min(max(float(raw), 0.1) + 0.1, RATE_LIMIT_MAX_DELAY)
        except (TypeError, ValueError):
            pass
    return min(RATE_LIMIT_BASE_DELAY * (2 ** attempt), RATE_LIMIT_MAX_DELAY)


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

    Trata dois erros esperados do provedor:

    - 429 de rate limit: a chamada e repetida respeitando o `retry-after`.
    - 400 `json_validate_failed`: modelos com raciocinio longo as vezes estouram
      o orcamento de tokens antes de fechar o JSON. A chamada e repetida com o
      raciocinio desligado.
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
        STATS["calls"] += 1
        response = get_client().chat.completions.create(**kwargs)
        return (response.choices[0].message.content or "").strip()

    def _rejects_effort(error: Exception) -> bool:
        """Alguns modelos nao aceitam `reasoning_effort="none"`.

        Os `openai/gpt-oss-*` respondem 400 exigindo low/medium/high. Sem isso
        eles nao servem como JUDGE_MODEL, que roda sempre com "none".
        """
        return "reasoning_effort" in str(error)

    def _call_with_retry(effort: str | None) -> str:
        for attempt in range(MAX_RATE_LIMIT_RETRIES + 1):
            try:
                return _call(effort)
            except Exception as error:
                if not _is_rate_limit(error):
                    raise
                delay = _retry_delay(error, attempt)
                exhausted = attempt == MAX_RATE_LIMIT_RETRIES
                over_budget = (
                    STATS["wait_seconds"] + delay > RATE_LIMIT_TOTAL_WAIT_BUDGET
                )
                if exhausted or over_budget:
                    raise RateLimitExhausted(
                        _rate_limit_help(model, error)
                    ) from error
                _warn_rate_limit(model, delay)
                STATS["retries"] += 1
                STATS["wait_seconds"] += delay
                time.sleep(delay)
        raise RateLimitExhausted("rate limit sem tentativas restantes")

    try:
        return _call_with_retry(reasoning_effort)
    except RateLimitExhausted:
        raise
    except Exception as error:
        if _rejects_effort(error):
            return _call_with_retry(None)
        if reasoning_effort == "none":
            raise
        try:
            return _call_with_retry("none")
        except RateLimitExhausted:
            raise
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


def _report_stats() -> None:
    if not os.getenv("RAG_DEBUG_RATE_LIMIT"):
        return
    if not STATS["calls"]:
        return
    print(
        f"[rate limit] {STATS['calls']} chamadas, {STATS['retries']} repeticoes, "
        f"{STATS['wait_seconds']:.1f}s de espera",
        file=sys.stderr,
    )


atexit.register(_report_stats)
