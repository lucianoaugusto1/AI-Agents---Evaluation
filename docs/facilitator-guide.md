# Guia do facilitador

## Historia do sistema

A ACME Corp criou um assistente interno para responder perguntas sobre RH, Financeiro e TI. O prototipo foi montado rapido, com agentes especializados e um retriever simples sobre documentos Markdown.

O problema: a demo parece boa, mas a evaluation revela riscos classicos de sistemas com LLM.

## Bugs intencionais

- `finance_agent` usa valores de politica antiga: 15 dias corridos e R$ 120.
- `finance_agent` permite compra de software sem aprovacao previa.
- `hr_agent` responde sobre salario individual em vez de recusar/escalar.
- `it_agent` vaza um codigo falso de bypass diante de prompt injection.
- `it_agent` retorna texto livre em um caso, quebrando contrato JSON.
- `general_agent` inventa permissao quando nao ha contexto.
- `retrieve` nao filtra documento obsoleto.
- `retrieve` nao possui limiar para ausencia de contexto util.

## Como conduzir

1. Peça para todos rodarem `uv sync`.
2. Peça para todos rodarem `uv run python -m evals.run_eval --verbose`.
3. Se quiser demonstrar produto real, suba a API com `uv run uvicorn src.acme_support_ai.api:app --reload`.
4. Se houver Langfuse ou Braintrust configurado, rode a suite com `--trace-provider langfuse` ou `--trace-provider braintrust`.
5. Dê 5 minutos para leitura dos failures.
6. Peça para escolherem uma classe de bug por vez.
7. Incentive alteracoes pequenas e novas execucoes da suite.
8. No final, cada grupo apresenta score antes/depois e diagnostico.

## Observabilidade no workshop

Recomendacao pratica:

- Use `--trace-provider local` como modo padrao para todos.
- Use Langfuse ou Braintrust em uma maquina do facilitador para mostrar traces, scores por caso e comparacao entre runs.
- Nao dependa de conta externa para o desafio funcionar.

Comandos:

```bash
uv run python -m evals.run_eval --verbose --trace-provider local
```

```bash
uv sync --extra observability
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

```bash
uv sync --extra observability
uv run bt eval evals/braintrust_eval.py
```

Referencias:

- Langfuse SDK: https://langfuse.com/docs/observability/sdk/overview
- Braintrust evaluations: https://www.braintrust.dev/docs/evaluate/run-evaluations

## Caminho de correcao esperado

Solucoes possiveis:

- Filtrar documentos obsoletos no retrieval.
- Responder com base no texto atual dos documentos, nao em valores hard-coded.
- Retornar sempre JSON no contrato esperado.
- Escalar casos com dado sensivel, compra fora de politica e ausencia de contexto.
- Recusar pedidos de prompt interno, bypass ou segredo.
- Ajustar roteamento para casos de TI genericos.

## Premiacoes sugeridas

- Maior melhoria de score.
- Melhor bug encontrado.
- Melhor explicacao de risco residual.
