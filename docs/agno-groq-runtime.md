# Runtime Agno + Groq

O projeto tem dois modos de execucao:

- `scripted`: deterministico, sem chamada externa, usado como baseline do desafio.
- `agno`: agentes reais usando Agno, modelo Groq e tools locais.

Use o modo `agno` quando quiser demonstrar um fluxo mais parecido com producao: agentes com papeis especializados, uso de ferramentas e respostas variaveis avaliadas pela mesma suite.

## Onde ele se encaixa

```text
FastAPI ou CLI
      |
      v
orchestrator.answer_question()
      |
      +--> ACME_AGENT_RUNTIME=scripted -> agents.py
      |
      +--> ACME_AGENT_RUNTIME=agno
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

Essas tools retornam dados ficticios da ACME. Quando o runtime `agno` esta ativo, o resultado das tools pode ser enviado ao modelo da Groq como contexto.

## Setup

```bash
uv sync --extra agents
cp .env.example .env
```

Edite `.env`:

```bash
ACME_AGENT_RUNTIME=agno
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
```

O modelo default e `openai/gpt-oss-120b`, recomendado pela documentacao de deprecacao da Groq como substituto para `llama-3.3-70b-versatile` em contas free/developer.

## Rodar uma pergunta

```bash
ACME_AGENT_RUNTIME=agno uv run python -m src.acme_support_ai.cli "Qual é o prazo para pedir reembolso de viagem?"
```

## Rodar a evaluation com agentes reais

```bash
ACME_AGENT_RUNTIME=agno uv run python -m evals.run_eval --verbose
```

## Rodar com Langfuse

```bash
uv sync --extra full
ACME_AGENT_RUNTIME=agno uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

## O que observar

Compare o runtime `scripted` e o runtime `agno`:

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
