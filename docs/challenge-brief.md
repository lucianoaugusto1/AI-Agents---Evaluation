# Brief do desafio

Vocês foram chamados como consultoria para avaliar o assistente interno da ACME Corp.

O sistema usa agentes reais de RH, Financeiro e TI com Agno + Groq e tools locais. A empresa quer colocar esse assistente em producao, mas percebeu alguns comportamentos estranhos e pediu uma avaliacao antes de escalar o uso.

## Queixas da ACME

A empresa trouxe estes sintomas:

- alguns colaboradores receberam prazos diferentes para reembolso;
- algumas respostas parecem usar politica antiga;
- em perguntas sensiveis de RH, o assistente da detalhes demais;
- algumas respostas quebram o formato esperado pela API;
- quando nao encontra uma politica clara, o assistente responde com confiança demais;
- o time de TI suspeita que pedidos maliciosos podem influenciar a resposta.

A partir dessas queixas, foi criado um Golden Dataset com o comportamento ideal esperado. O papel do grupo e usar a Evaluation para descobrir onde o sistema esta falhando e corrigir a causa.

## Missao

1. Rode a evaluation inicial.
2. Analise os casos que falham.
3. Descubra a causa provavel de cada sintoma.
4. Corrija o sistema.
5. Rode a evaluation novamente.
6. Reporte o que foi encontrado.

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

Configure `.env` com `GROQ_API_KEY` antes de executar o sistema.

```bash
uv run python -m evals.run_eval --verbose
```

```bash
uv run uvicorn src.acme_support_ai.api:app --reload
```

```bash
uv run python -m src.acme_support_ai.cli "Qual é o prazo para pedir reembolso de viagem?"
```

## Runtime real com agentes

```bash
uv run python -m src.acme_support_ai.cli "Qual é o prazo para pedir reembolso de viagem?"
```

Com Langfuse:

```bash
uv sync
uv run python scripts/setup_langfuse.py
uv run python -m evals.run_eval --verbose --trace-provider langfuse --run-name tentativa-01
```

O runtime real envia perguntas e contexto ficticio do projeto para Groq.

Leia `docs/agno-groq-runtime.md` para ver arquitetura, tools e setup.

## Observabilidade

Modo local:

```bash
uv run python -m evals.run_eval --trace-provider local
```

Modo Langfuse, se o facilitador fornecer chaves:

```bash
uv sync
uv run python scripts/setup_langfuse.py
uv run python -m evals.run_eval --trace-provider langfuse --run-name tentativa-01
```

Leia `docs/langfuse-setup.md` para configurar as credenciais e entender onde a Dataset Run aparece.

## Entrega

Preencha:

- Score inicial:
- Score final:
- Falha 1:
- Falha 2:
- Falha 3:
- Mudancas feitas:
- Risco ou teste que ainda falta:
