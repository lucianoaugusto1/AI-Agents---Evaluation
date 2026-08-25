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

Por tras da API existe um sistema real de agentes com Agno + Groq:

```text
FastAPI -> orchestrator -> Agno Team -> Groq model -> tools -> JSON response
```

Os agentes especializados usam tools locais para consultar politicas, versoes de documentos, matriz de aprovacao, perfis ficticios e tickets simulados. Os problemas do desafio aparecem em instrucoes, roteamento, uso de contexto, documentos obsoletos e decisoes de seguranca.

Esse desenho simula um produto real o suficiente para discutir:

- qualidade de resposta;
- faithfulness em cima de politicas internas;
- roteamento entre agentes;
- regressao entre versoes;
- observabilidade de traces e scores com Langfuse.

## Apresentacao do workshop

A apresentacao HTML esta no proprio repositorio:

```text
presentation/index.html
```

Abra esse arquivo no navegador para conduzir a parte teorica e introduzir o desafio pratico.

## Objetivo do desafio

Melhorar o score do sistema sem editar o dataset ou o avaliador.

Arquivos que podem ser alterados durante o desafio:

- `src/acme_support_ai/agno_runtime.py`
- `src/acme_support_ai/orchestrator.py`
- `src/acme_support_ai/knowledge_base.py`
- `src/acme_support_ai/tools.py`
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
uv sync --extra full
```

Copie o arquivo de exemplo e preencha a chave da Groq:

```bash
cp .env.example .env
# preencha GROQ_API_KEY
```

O sistema usa agentes reais. Perguntas e contexto ficticio retornado pelas tools sao enviados para Groq.

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

## Runtime com Agno + Groq

O projeto usa Agno + Groq como runtime padrao. Ele envia a pergunta e o contexto ficticio retornado pelas tools para a API da Groq.

Instale as dependencias:

```bash
uv sync --extra agents
```

Configure:

```bash
cp .env.example .env
# preencha GROQ_API_KEY
GROQ_MODEL=qwen/qwen3.6-27b
```

Rode uma pergunta:

```bash
uv run python -m src.acme_support_ai.cli "Qual é o prazo para pedir reembolso de viagem?"
```

Rode a evaluation usando agentes reais:

```bash
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

Esse comando envia todas as perguntas do golden dataset e o contexto ficticio retornado pelas tools para Groq. Use apenas em ambiente aprovado para o workshop.

### Tools disponiveis para os agentes

- `search_policy_documents`: busca documentos de politica.
- `list_policy_versions`: lista versoes atuais e obsoletas.
- `get_employee_profile`: retorna perfil ficticio para decisoes de privacidade.
- `check_approval_matrix`: consulta regras de aprovacao.
- `create_support_ticket`: cria ticket simulado.

### Onde fica o codigo

- Runtime Agno/Groq: `src/acme_support_ai/agno_runtime.py`
- Tools dos agentes: `src/acme_support_ai/tools.py`
- Entrada unica do runtime: `src/acme_support_ai/orchestrator.py`

Guia detalhado:

```text
docs/agno-groq-runtime.md
docs/evaluation-findings-guide.md
```

## Observabilidade

O padrao de observabilidade do projeto e Langfuse. Ele entra depois que cada caso do golden dataset e executado:

```text
golden_dataset -> Agno+Groq agents -> judge -> scores -> Langfuse trace
```

Para configurar, siga o guia:

```text
docs/langfuse-setup.md
```

O trace local continua disponivel como fallback sem conta Langfuse. Ele ainda usa os agentes Agno + Groq, mas grava a observabilidade em arquivo JSONL:

```bash
uv run python -m evals.run_eval --verbose --trace-provider local
```

Isso cria arquivos em `runs/`.

Use esse modo quando todos os participantes tiverem Groq, mas nao tiverem conta Langfuse.

Para usar Langfuse no fluxo principal:

```bash
uv sync --extra full
cp .env.example .env
# preencha LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY e LANGFUSE_BASE_URL
uv run python -m evals.run_eval --trace-provider langfuse
```

Recomendacao para workshop: use `--trace-provider local` se a turma nao tiver credenciais, e use `--trace-provider langfuse` na maquina do facilitador para mostrar traces, scores e comparacao entre runs.

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

- Score inicial esperado: abaixo da meta
- Meta do desafio: `0.85+`
- Vitoria tecnica: melhorar score e explicar quais problemas foram encontrados

O score inicial pode variar porque o runtime usa IA real. Registre o primeiro resultado antes de mexer no sistema e compare com o resultado final.

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
- Langfuse integrations: https://langfuse.com/integrations
- Langfuse Python reference: https://python.reference.langfuse.com/langfuse
- Groq + Agno: https://console.groq.com/docs/agno
- Groq tool use: https://console.groq.com/docs/tool-use
- Agno docs: https://docs.agno.com/
- uv: https://docs.astral.sh/uv/
