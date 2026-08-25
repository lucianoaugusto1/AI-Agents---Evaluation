# ACME Agents Eval Challenge

Projeto didatico para workshop de Evaluation em sistemas com LLM.

A ACME Corp, empresa ficticia usada no exercicio, tem um assistente interno com agentes especializados em RH, Financeiro, TI e atendimento geral. O sistema parece funcionar em demos simples, mas apresenta problemas comuns em projetos reais com LLM: usa politica antiga, inventa respostas sem contexto, ignora formato esperado, vaza instrucao indevida e falha em casos ambiguos.

O desafio dos participantes e usar Evaluation para diagnosticar esses problemas, corrigir o sistema e demonstrar melhoria com metricas.

## Contexto do produto

O assistente responde perguntas internas de colaboradores sobre:

- viagens e reembolsos;
- beneficios, ferias e politicas de RH;
- acesso, VPN, MFA e seguranca;
- perguntas gerais quando nao ha agente especializado.

Por tras da API existe um sistema simples de agentes:

```text
FastAPI -> orchestrator -> retriever -> specialist agent -> JSON response
```

Esse desenho simula um produto real o suficiente para discutir:

- qualidade de resposta;
- faithfulness em cima de politicas internas;
- roteamento entre agentes;
- regressao entre versoes;
- observabilidade de traces e scores.

## Objetivo do desafio

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

## O que e esperado

Ao final, cada grupo deve conseguir explicar:

- qual era o score inicial;
- quais falhas foram encontradas;
- quais mudancas foram feitas;
- qual foi o score final;
- qual risco ainda ficou aberto.

Nao basta subir o score por tentativa e erro. A entrega precisa conectar falha, evidencia e correcao.

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

Exemplo para rodar a evaluation pela API:

```bash
curl -X POST http://127.0.0.1:8000/eval/run \
  -H "content-type: application/json" \
  -d '{"trace_provider":"local"}'
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

Use esse modo quando todos os participantes precisarem rodar o desafio sem depender de conta externa.

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

Recomendacao para workshop: use `--trace-provider local` como padrao e deixe Langfuse ou Braintrust para demonstracao do facilitador, caso as credenciais ja estejam configuradas.

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

Baseline atual esperado:

```text
overall      0.611
relevance    0.450
faithfulness 0.625
format       0.900
safety       0.460
```

## Entrega dos grupos

Cada grupo deve enviar:

- Score inicial
- Score final
- 3 principais falhas encontradas
- Mudancas feitas
- 1 teste que ainda falha ou risco restante

Template de entrega:

```text
Grupo:
Score inicial:
Score final:

Falha 1:
Evidencia:
Correcao:

Falha 2:
Evidencia:
Correcao:

Falha 3:
Evidencia:
Correcao:

Risco restante:
```

## Dica

Nao comece alterando tudo. Rode a evaluation, olhe os piores casos e corrija uma classe de erro por vez.

## Fontes das integracoes

- Langfuse SDK: https://langfuse.com/docs/observability/sdk/overview
- Langfuse observation types: https://langfuse.com/docs/observability/features/observation-types
- Braintrust evaluations: https://www.braintrust.dev/docs/evaluate/run-evaluations
- Braintrust traces: https://www.braintrust.dev/docs/observe/examine-traces
- uv: https://docs.astral.sh/uv/
