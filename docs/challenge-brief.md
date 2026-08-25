# Brief do desafio

Vocês fazem parte do time responsavel pelo assistente interno da ACME Corp.

O sistema usa um orquestrador simples com agentes de RH, Financeiro, TI e Geral. A empresa quer colocar esse assistente em producao, mas antes precisa de uma suite minima de Evaluation.

## Missao

1. Rode a evaluation inicial.
2. Analise os casos que falham.
3. Corrija o sistema.
4. Rode a evaluation novamente.
5. Reporte o que foi encontrado.

## Regras

- Nao edite `evals/golden_dataset.jsonl`.
- Nao edite `evals/judge.py`.
- Nao remova casos de teste.
- Voce pode alterar agentes, roteamento, retrieval e documentos de politica.
- Otimizar o score sem preservar qualidade real nao conta como solucao.

## Comandos

```bash
uv sync
```

```bash
uv run python -m evals.run_eval --verbose
```

```bash
uv run uvicorn src.acme_support_ai.api:app --reload
```

```bash
uv run python -m src.acme_support_ai.cli "Qual é o prazo para pedir reembolso de viagem?"
```

## Observabilidade

Modo local:

```bash
uv run python -m evals.run_eval --trace-provider local
```

Modo Langfuse ou Braintrust, se o facilitador fornecer chaves:

```bash
uv sync --extra observability
uv run python -m evals.run_eval --trace-provider langfuse
uv run python -m evals.run_eval --trace-provider braintrust
```

## Entrega

Preencha:

- Score inicial:
- Score final:
- Falha 1:
- Falha 2:
- Falha 3:
- Mudancas feitas:
- Risco ou teste que ainda falta:
