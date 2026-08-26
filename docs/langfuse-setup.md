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

## 2. Instalar dependências

```bash
uv sync
```

## 3. Configurar variaveis de ambiente

Copie o exemplo:

```bash
cp .env.example .env
```

Preencha:

```bash
GROQ_API_KEY=gsk_...
GROQ_MODEL=qwen/qwen3.6-27b
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Se estiver usando Langfuse self-hosted, troque `LANGFUSE_BASE_URL` pela URL da sua instancia.

## 4. Criar dataset e code evaluators no Langfuse

O projeto inclui um script para subir o golden dataset e criar os code evaluators determinísticos no Langfuse:

```bash
uv run python scripts/setup_langfuse.py
```

Antes de chamar a API do Langfuse, revise o payload com:

```bash
uv run python scripts/setup_langfuse.py --dry-run
```

O script cria:

- dataset `acme-agents-golden-dataset`;
- evaluator `acme-json-contract`;
- evaluator `acme-golden-dataset-rules`;
- evaluator `acme-business-risk-flags`.
- evaluation rule `acme-json-contract-live-observations`;
- evaluation rule `acme-business-risk-flags-live-observations`;
- evaluation rule `acme-golden-dataset-rules-experiments`.

As duas primeiras rules avaliam observations live. A rule `acme-golden-dataset-rules-experiments` usa target `experiment`, porque precisa ler o `expected_output` dos itens do dataset.

Importante: Langfuse executa um preflight quando uma code evaluation rule é criada com `enabled=true`. Se a instância rejeitar esse preflight, o script cria a rule desativada e mostra um aviso. Nesse caso, abra a rule no Langfuse, rode o teste do evaluator com uma observation/experiment de exemplo e habilite pela UI. Code evaluators também dependem do runtime/dispatcher de code evaluation estar disponível no projeto.

Se um evaluator com o mesmo nome já existir, o script pula a criação para evitar gerar nova versão acidental. Para criar uma nova versão explicitamente:

```bash
uv run python scripts/setup_langfuse.py --skip-dataset --force-evaluator-version
```

Para recriar apenas as rules:

```bash
uv run python scripts/setup_langfuse.py --skip-dataset --skip-evaluators
```

Os evaluators ficam versionados no repo em:

```text
evals/langfuse_evaluators/
```

Os code evaluators usam apenas lógica determinística: parse de JSON, keywords esperadas, citações obrigatórias, claims proibidas, escalonamento esperado e flags de risco de negócio. Eles seguem o contrato atual de Code Evaluators do Langfuse, que executa código Python ou TypeScript sobre observations/experiments.

Observação: a API pública de criação de evaluators ainda é marcada como unstable pelo Langfuse. Se a sua instância bloquear esse endpoint, use os arquivos em `evals/langfuse_evaluators/` para criar os evaluators manualmente pela UI.

## 5. Rodar a evaluation com trace

```bash
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

Ao final, o runner chama `flush()` para enviar os eventos pendentes.

O fluxo recomendado para workshop é:

```bash
uv sync
cp .env.example .env
uv run python scripts/setup_langfuse.py --dry-run
uv run python scripts/setup_langfuse.py
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

Esse fluxo deixa o golden dataset e os evaluators disponíveis no Langfuse antes de comparar runs.

## 6. O que olhar no Langfuse

Durante o workshop, abra os traces e compare:

- quais perguntas falharam;
- qual agente respondeu;
- qual resposta foi gerada;
- quais scores ficaram baixos;
- quais problemas o judge reportou;
- como o score muda depois de cada correcao.

## 7. Como usar isso na discussao

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
