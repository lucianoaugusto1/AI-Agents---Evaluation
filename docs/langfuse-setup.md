# Configurando Langfuse no desafio

Langfuse e a ferramenta padrao de observabilidade deste projeto. Ele permite enxergar cada caso do golden dataset como um trace, com input, output, metadata e scores.

## Onde Langfuse se encaixa

```text
evals/golden_dataset.jsonl
        |
        v
evals/run_eval.py
        |
        +--> src/acme_support_ai/orchestrator.py
        |       |
        |       +--> Agno + Groq agents
        |               |
        |               +--> tools locais
        |
        +--> evals/judge.py
        |       |
        |       +--> relevance, faithfulness, format, safety
        |
        v
evals/observability.py
        |
        +--> Langfuse trace + scores
```

O arquivo principal da integracao e `evals/observability.py`. A classe `LangfuseObserver` cria uma observation por caso avaliado e envia os scores:

- `overall`
- `relevance`
- `faithfulness`
- `format`
- `safety`

A resposta avaliada vem de agentes reais executados em `src/acme_support_ai/agno_runtime.py`. As tools usadas por esses agentes ficam em `src/acme_support_ai/tools.py`.

## 1. Criar ou escolher um projeto no Langfuse

Use Langfuse Cloud ou uma instancia self-hosted.

- Langfuse Cloud: https://cloud.langfuse.com
- Visao geral do SDK: https://langfuse.com/docs/observability/sdk/overview
- Tipos de observation: https://langfuse.com/docs/observability/features/observation-types
- Integracoes Langfuse: https://langfuse.com/integrations

No projeto Langfuse, gere as API keys do ambiente que sera usado no workshop.

## 2. Instalar dependencias opcionais

```bash
uv sync --extra full
```

## 3. Configurar variaveis de ambiente

Copie o exemplo:

```bash
cp .env.example .env
```

Preencha:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Se estiver usando Langfuse self-hosted, troque `LANGFUSE_BASE_URL` pela URL da sua instancia.

## 4. Rodar a evaluation com trace

```bash
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

Com todas as dependencias opcionais:

```bash
uv sync --extra full
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

Ao final, o runner chama `flush()` para enviar os eventos pendentes.

## 5. O que olhar no Langfuse

Durante o workshop, abra os traces e compare:

- quais perguntas falharam;
- qual agente respondeu;
- qual resposta foi gerada;
- quais scores ficaram baixos;
- quais problemas o judge reportou;
- como o score muda depois de cada correcao.

## 6. Como usar isso na discussao

Use Langfuse para mostrar que Evaluation nao e apenas uma nota final. Ela ajuda o time a investigar:

- se o problema esta no roteamento;
- se o problema esta no contexto recuperado;
- se o agente esta usando regra antiga;
- se o output viola formato;
- se a resposta e util, mas nao fiel ao contexto.
- se uma alteracao melhora ou piora o run anterior.

## Fallback sem conta Langfuse

Se alguem nao tiver credenciais Langfuse, rode:

```bash
uv run python -m evals.run_eval --verbose --trace-provider local
```

Esse modo gera arquivos JSONL em `runs/` com os mesmos eventos principais.
Ele ainda executa os agentes Agno + Groq, entao `GROQ_API_KEY` continua obrigatoria.
