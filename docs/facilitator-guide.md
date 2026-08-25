# Guia do facilitador

## Historia do sistema

A ACME Corp criou um assistente interno para responder perguntas sobre RH, Financeiro e TI. O prototipo usa agentes reais com Agno + Groq, tools locais e um retriever simples sobre documentos Markdown.

O problema: a demo parece boa, mas a evaluation revela riscos classicos de sistemas com LLM.

## Bugs intencionais

- o agente financeiro pode usar valores de politica antiga: 15 dias corridos e R$ 120.
- o agente financeiro pode permitir compra de software sem aprovacao previa.
- o agente de RH pode responder sobre salario individual em vez de recusar/escalar.
- o agente de TI pode falhar diante de prompt injection.
- o sistema pode retornar texto fora do contrato JSON esperado.
- o sistema pode inventar permissao quando nao ha contexto.
- `retrieve` nao filtra documento obsoleto.
- `retrieve` nao possui limiar para ausencia de contexto util.

## Como conduzir

1. Peça para todos rodarem `uv sync --extra full`.
2. Peça para todos rodarem `uv run python -m evals.run_eval --verbose`.
3. Se quiser demonstrar produto real, suba a API com `uv run uvicorn src.acme_support_ai.api:app --reload`.
4. Garanta que `GROQ_API_KEY` esteja configurado antes da execucao.
5. Se houver Langfuse configurado, rode a suite com `--trace-provider langfuse`.
6. Dê 5 minutos para leitura dos failures.
7. Peça para escolherem uma classe de bug por vez.
8. Incentive alteracoes pequenas e novas execucoes da suite.
9. No final, cada grupo apresenta score antes/depois e diagnostico.

## Observabilidade no workshop

Recomendacao pratica:

- Use `--trace-provider local` quando a turma tiver Groq, mas nao tiver credenciais Langfuse.
- Use Langfuse em uma maquina do facilitador para mostrar traces, scores por caso e comparacao entre runs.
- Garanta credenciais Groq para cada grupo ou execute a suite em uma maquina compartilhada do facilitador.

Comandos:

```bash
uv run python -m evals.run_eval --verbose --trace-provider local
```

```bash
uv sync --extra full
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

Referencias:

- Langfuse SDK: https://langfuse.com/docs/observability/sdk/overview
- Langfuse observation types: https://langfuse.com/docs/observability/features/observation-types

## Agentes reais com Agno + Groq

O projeto usa apenas agentes reais com Groq e tools locais.

Para demonstrar:

```bash
uv sync --extra full
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

Use esse modo para mostrar:

- chamada real ao modelo;
- escolha de agente;
- uso de tools;
- impacto de prompt/instrucao;
- traces e scores no Langfuse.

Referencias:

- Groq + Agno: https://console.groq.com/docs/agno
- Groq tool use: https://console.groq.com/docs/tool-use
- Agno docs: https://docs.agno.com/
- Guia de achados esperados: `docs/evaluation-findings-guide.md`

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
