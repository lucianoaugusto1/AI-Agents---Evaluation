# ACME Agents Eval Challenge

Projeto didatico para workshop de Evaluation em sistemas com LLM.

A ACME Corp tem um assistente interno com agentes especializados em RH, Financeiro e TI. O sistema parece funcionar em demos simples, mas tem bugs intencionais: usa politica antiga, inventa respostas sem contexto, ignora formato, vaza instrucao interna e falha em casos ambíguos.

O desafio dos participantes e usar Evaluation para diagnosticar e corrigir o sistema.

## Objetivo

Melhorar o score do sistema sem editar o dataset ou o avaliador.

Arquivos que podem ser alterados durante o desafio:

- `src/acme_support_ai/agents.py`
- `src/acme_support_ai/orchestrator.py`
- `src/acme_support_ai/knowledge_base.py`
- `src/acme_support_ai/policies/*.md`

Arquivos que representam a suite de evaluation e nao devem ser editados:

- `evals/golden_dataset.jsonl`
- `evals/judge.py`
- `evals/run_eval.py`

## Setup com uv

```bash
uv sync
```

## Como rodar a API

```bash
uv run uvicorn src.acme_support_ai.api:app --reload
```

Depois acesse:

- `GET http://127.0.0.1:8000/health`
- `POST http://127.0.0.1:8000/ask`
- `POST http://127.0.0.1:8000/eval/run`

Exemplo:

```bash
curl -X POST http://127.0.0.1:8000/ask \
  -H "content-type: application/json" \
  -d '{"question":"Qual é o prazo para pedir reembolso de viagem?"}'
```

## Como rodar a Evaluation

```bash
uv run python -m evals.run_eval
```

Para ver detalhes caso a caso:

```bash
uv run python -m evals.run_eval --verbose
```

Para rodar os testes da estrutura do projeto:

```bash
uv run python -m unittest discover
```

Para testar uma pergunta manual:

```bash
uv run python -m src.acme_support_ai.cli "Qual e o prazo para pedir reembolso de viagem?"
```

## Observabilidade

O runner local funciona sem conta externa. Para gerar um arquivo de trace em JSONL:

```bash
uv run python -m evals.run_eval --verbose --trace-provider local
```

Isso cria arquivos em `runs/`.

Para usar Langfuse:

```bash
uv sync --extra observability
cp .env.example .env
# preencha LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY e LANGFUSE_BASE_URL
uv run python -m evals.run_eval --trace-provider langfuse
```

Para usar Braintrust como observabilidade:

```bash
uv sync --extra observability
cp .env.example .env
# preencha BRAINTRUST_API_KEY
uv run python -m evals.run_eval --trace-provider braintrust
```

Para usar o fluxo nativo de experimentos do Braintrust:

```bash
uv sync --extra observability
uv run bt eval evals/braintrust_eval.py
```

## Score

O score final usa quatro criterios:

- `relevance`: respondeu ao que foi perguntado?
- `faithfulness`: a resposta esta sustentada pelos documentos citados?
- `format`: retornou o contrato esperado?
- `safety`: respeitou politicas e nao vazou informacao indevida?

Pesos:

```text
40% faithfulness + 30% relevance + 20% format + 10% safety
```

## Meta sugerida

- Baseline esperado: abaixo de `0.70`
- Meta do desafio: `0.85+`
- Vitoria tecnica: melhorar score e explicar quais problemas foram encontrados

## Entrega dos grupos

Cada grupo deve enviar:

- Score inicial
- Score final
- 3 principais falhas encontradas
- Mudancas feitas
- 1 teste que ainda falha ou risco restante

## Dica

Nao comece alterando tudo. Rode a evaluation, olhe os piores casos e corrija uma classe de erro por vez.

## Fontes das integracoes

- Langfuse SDK: https://langfuse.com/docs/observability/sdk/overview
- Langfuse observation types: https://langfuse.com/docs/observability/features/observation-types
- Braintrust evaluations: https://www.braintrust.dev/docs/evaluate/run-evaluations
- Braintrust traces: https://www.braintrust.dev/docs/observe/examine-traces
- uv: https://docs.astral.sh/uv/
