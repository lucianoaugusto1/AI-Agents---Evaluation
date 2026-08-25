# Runtime Agno + Groq

O projeto usa agentes reais com Agno, modelo Groq e tools locais. Esse fluxo foi escolhido para deixar o desafio mais proximo de producao: agentes com papeis especializados, uso de ferramentas e respostas variaveis avaliadas pela mesma suite.

## Onde ele se encaixa

```text
FastAPI ou CLI
      |
      v
orchestrator.answer_question()
      |
      +--> agno_runtime.py
      +--> Agno Team em modo route
      +--> Groq model
      +--> tools.py
```

## Tools disponiveis

As tools ficam em `src/acme_support_ai/tools.py`:

- `search_policy_documents`: busca documentos de politica.
- `list_policy_versions`: lista versoes atuais e obsoletas.
- `get_employee_profile`: retorna perfil ficticio para decisoes de privacidade.
- `check_approval_matrix`: consulta regras de aprovacao.
- `create_support_ticket`: cria ticket simulado.

Essas tools retornam dados ficticios da ACME. O resultado das tools pode ser enviado ao modelo da Groq como contexto.

## Setup

```bash
uv sync --extra agents
cp .env.example .env
```

Edite `.env`:

```bash
GROQ_API_KEY=gsk_...
GROQ_MODEL=qwen/qwen3.6-27b
```

O modelo default e `qwen/qwen3.6-27b`, uma das alternativas recomendadas pela documentacao de deprecacao da Groq para substituir `llama-3.3-70b-versatile` em contas free/developer. Ele tambem funcionou melhor neste projeto com tool calling + resposta JSON textual.

## Rodar uma pergunta

```bash
uv run python -m src.acme_support_ai.cli "Qual é o prazo para pedir reembolso de viagem?"
```

## Rodar a evaluation com agentes reais

```bash
uv run python -m evals.run_eval --verbose
```

Esse comando envia todas as perguntas do golden dataset e o contexto ficticio retornado pelas tools para Groq. Rode apenas com autorizacao do facilitador.

## Rodar com Langfuse

```bash
uv sync --extra full
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

## O que observar

Compare os runs antes e depois das alteracoes:

- score total;
- faithfulness;
- casos em que o modelo usa documento obsoleto;
- casos em que a tool certa foi chamada, mas a resposta ainda falhou;
- variacao entre runs;
- custo e latencia percebida.

## Links

- Groq + Agno: https://console.groq.com/docs/agno
- Groq tool use: https://console.groq.com/docs/tool-use
- Groq models: https://console.groq.com/docs/models
- Groq deprecations: https://console.groq.com/docs/deprecations
- Agno docs: https://docs.agno.com/
