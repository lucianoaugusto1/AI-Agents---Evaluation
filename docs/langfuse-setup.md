# Configurando Langfuse no desafio

Langfuse e a ferramenta padrao para rodar, observar e comparar as evaluations deste projeto.
Ele permite enxergar cada caso do golden dataset como item de uma Dataset Run, com input,
output, metadata, scores e link para o trace.

## Onde Langfuse se encaixa

```text
evals/golden_dataset.jsonl
        |
        v
scripts/setup_langfuse.py
        |
        +--> Langfuse dataset
        |
        v
evals/run_eval.py --trace-provider langfuse
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
Langfuse Dataset Run / Experiment
        |
        +--> traces + item scores + run score
```

O arquivo principal da integracao e `evals/run_eval.py`. Quando `--trace-provider langfuse`
e usado, ele busca o dataset `acme-agents-golden-dataset` no Langfuse e executa
`dataset.run_experiment(...)`. Isso cria uma Dataset Run comparavel na UI do Langfuse.

O Langfuse nao executa os agentes sozinho. O script local chama a API/SDK do Langfuse,
executa os agentes Agno + Groq, avalia a resposta e grava output, trace e scores na Dataset Run.

Os evaluators do SDK anexam estes scores em cada item da run:

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

## 4. Criar dataset no Langfuse

O projeto inclui um script para subir o golden dataset no Langfuse. Ele tambem cria code
evaluators e rules desativadas como material opcional, mas o fluxo principal de scoring roda
pelos evaluators do `evals/run_eval.py` dentro da Dataset Run.

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
- evaluation rule desativada `acme-json-contract-live-observations`;
- evaluation rule desativada `acme-business-risk-flags-live-observations`;
- evaluation rule desativada `acme-golden-dataset-rules-experiments`.

As duas primeiras rules avaliam observations live. A rule `acme-golden-dataset-rules-experiments` usa target `experiment`, porque precisa ler o `expected_output` dos itens do dataset.

Importante: essas rules server-side nao sao necessarias para o workshop. A comparacao entre
tentativas acontece na Dataset Run criada por `evals/run_eval.py`, e os scores ficam ativos
mesmo com as rules desativadas.

Se quiser testar Code Evaluators server-side do Langfuse, rode:

```bash
uv run python scripts/setup_langfuse.py --enable-rules
```

Langfuse executa um preflight quando uma code evaluation rule é criada com `enabled=true`. Se a instância rejeitar esse preflight, mantenha a rule desativada e continue usando a Dataset Run via SDK. Code evaluators também dependem do runtime/dispatcher de code evaluation estar disponível no projeto.

Se um evaluator com o mesmo nome já existir, o script pula a criação para evitar gerar nova versão acidental. Para criar uma nova versão explicitamente:

```bash
uv run python scripts/setup_langfuse.py --skip-dataset --force-evaluator-version
```

Para recriar apenas as rules:

```bash
uv run python scripts/setup_langfuse.py --skip-dataset --skip-evaluators
```

Para tentar recriar e ativar as rules:

```bash
uv run python scripts/setup_langfuse.py --skip-dataset --skip-evaluators --enable-rules
```

Os evaluators ficam versionados no repo em:

```text
evals/langfuse_evaluators/
```

Os code evaluators usam apenas lógica determinística: parse de JSON, keywords esperadas, citações obrigatórias, claims proibidas, escalonamento esperado e flags de risco de negócio. Eles seguem o contrato atual de Code Evaluators do Langfuse, que executa código Python ou TypeScript sobre observations/experiments.

Observação: a API pública de criação de evaluators ainda é marcada como unstable pelo Langfuse. Se a sua instância bloquear esse endpoint, use os arquivos em `evals/langfuse_evaluators/` para criar os evaluators manualmente pela UI.

## 5. Rodar a Dataset Run no Langfuse

```bash
uv run python -m evals.run_eval --verbose --trace-provider langfuse --run-name tentativa-01
```

O comando cria uma Dataset Run/Experiment no Langfuse. Nessa execução, os evaluators do SDK
calculam `overall`, `relevance`, `faithfulness`, `format`, `safety` e `overall_avg`, gravando
os scores diretamente na run. Use `--run-name` para nomear as tentativas e facilitar a
comparacao na UI.

O fluxo recomendado para workshop é:

```bash
uv sync
cp .env.example .env
uv run python scripts/setup_langfuse.py --dry-run
uv run python scripts/setup_langfuse.py
uv run python -m evals.run_eval --verbose --trace-provider langfuse --run-name antes-das-correcoes
```

Depois das correcoes, rode novamente com outro nome:

```bash
uv run python -m evals.run_eval --verbose --trace-provider langfuse --run-name depois-das-correcoes
```

Esse fluxo deixa o Golden Dataset e as runs comparaveis dentro do Langfuse.

## 6. O que olhar no Langfuse

Durante o workshop, abra a Dataset Run no Langfuse e compare:

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
- se uma alteracao melhora ou piora a run anterior.

## Fallback sem conta Langfuse

Se alguem nao tiver credenciais Langfuse, rode:

```bash
uv run python -m evals.run_eval --verbose --trace-provider local
```

Esse modo gera arquivos JSONL em `runs/` com os mesmos eventos principais.
Ele ainda executa os agentes Agno + Groq, entao `GROQ_API_KEY` continua obrigatoria.
