# ACME Agents Eval Challenge

Projeto didatico para workshop de Evaluation em sistemas com LLM.

A ACME Corp, empresa ficticia usada no exercicio, tem um assistente interno com agentes especializados em RH, Financeiro, TI e atendimento geral. O sistema parece funcionar em demos simples, mas a empresa percebeu comportamentos estranhos em alguns atendimentos.

O desafio dos participantes e atuar como uma consultoria: ouvir as queixas da ACME, transformar o comportamento ideal em Golden Dataset, rodar Evaluation, investigar os sintomas, corrigir o sistema e demonstrar melhoria.

## As duas atividades do workshop

Este repositorio tem dois desafios de Evaluation, com a mesma logica e
sistemas diferentes:

| | Raiz do repositorio | `rag-evals/` |
| --- | --- | --- |
| Sistema | agentes Agno + Groq com tools | RAG sobre base de documentos |
| Falhas plantadas | prompt, roteamento, tools desatualizadas | chunking, indice, contexto, prompt |
| Metricas | relevance, faithfulness, format, safety | context precision/recall, faithfulness, answer relevancy, format |
| Observabilidade | Langfuse (dataset + code evaluators) | Langfuse (traces com spans de retrieve e generate) |

Os dois usam o mesmo `uv sync`, o mesmo `.env` e a mesma meta de score
(`0.85+`). O desafio de RAG esta documentado em `rag-evals/README.md` e o guia
do facilitador correspondente em `rag-evals/docs/guia-do-facilitador.md`.

```bash
uv run python rag-evals/scripts/run_eval.py --verbose
```

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

Os agentes especializados usam tools locais para consultar politicas, versoes de documentos, matriz de aprovacao, perfis ficticios e tickets simulados. Alguns componentes foram deixados com problemas de proposito, mas os participantes recebem primeiro os sintomas percebidos pela empresa, nao a lista de bugs.

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

Abra esse arquivo no navegador para conduzir a apresentacao. Ela cobre os conceitos principais
de Evaluation, mostra o case BIX + Grupo SOMA e termina com um unico slide explicando o
desafio pratico.

## Objetivo do desafio

Usar Evaluation para descobrir onde os agentes erram, corrigir o sistema e mostrar que a
qualidade melhorou. A regra principal: nao editar o Golden Dataset nem os avaliadores.

## Queixas da ACME

A empresa reportou alguns sintomas antes de pedir ajuda:

- colaboradores receberam prazos diferentes para reembolso;
- algumas respostas parecem usar politica antiga;
- em perguntas sensiveis de RH, o assistente da detalhes demais;
- algumas respostas quebram o formato esperado pela API;
- quando nao encontra uma politica clara, o assistente responde com confiança demais;
- o time de TI suspeita que pedidos maliciosos podem influenciar a resposta.

Essas queixas foram traduzidas em comportamento esperado no Golden Dataset. A Evaluation mede
se o sistema esta respeitando esse comportamento.

Arquivos que podem ser alterados durante o desafio:

- `src/acme_support_ai/agno_runtime.py`
- `src/acme_support_ai/orchestrator.py`
- `src/acme_support_ai/knowledge_base.py`
- `src/acme_support_ai/tools.py`
- `src/acme_support_ai/policies/*.md`

O prompt dos agentes fica em `src/acme_support_ai/agno_runtime.py` nas listas `FINANCE_PROMPT`, `HR_PROMPT`, `IT_PROMPT` e `SHARED_INSTRUCTIONS`. Ele foi deixado aberto para alterações e adições durante o exercício.

Arquivos que representam a suite de evaluation e nao devem ser editados:

- `evals/golden_dataset.jsonl`
- `evals/judge.py`
- `evals/run_eval.py`

## O que e esperado

Ao final, cada grupo deve conseguir explicar:

- qual era o score inicial;
- quais falhas foram encontradas;
- qual impacto essas falhas teriam para um cliente;
- quais mudancas foram feitas;
- qual foi o score final;
- qual risco ainda ficou aberto.

Nao basta subir o score por tentativa e erro. A entrega precisa explicar o problema, mostrar a
evidencia encontrada no Evaluation/Langfuse e justificar a correcao.

## Fluxo completo para validar o desafio

Use este caminho para simular a experiência dos participantes:

1. Gere ou separe as chaves:
   - `GROQ_API_KEY`;
   - `LANGFUSE_PUBLIC_KEY`;
   - `LANGFUSE_SECRET_KEY`;
   - `LANGFUSE_BASE_URL`.
2. Instale o projeto com `uv sync`.
3. Copie `.env.example` para `.env` e preencha as chaves.
4. Teste uma pergunta manual com a CLI.
5. Rode a Evaluation local para registrar o score inicial.
6. Configure dataset, evaluators e rules no Langfuse.
7. Rode a Evaluation enviando traces e scores para o Langfuse.
8. Analise os casos ruins, corrija agentes, ferramentas, regras ou políticas.
9. Rode a Evaluation novamente.
10. Compare score inicial e final, com evidências dos problemas encontrados.

Comandos principais:

```bash
uv sync
cp .env.example .env
uv run python -m src.acme_support_ai.cli "Qual é o prazo para pedir reembolso de viagem?"
uv run python -m evals.run_eval --verbose --trace-provider local
uv run python scripts/setup_langfuse.py --dry-run
uv run python scripts/setup_langfuse.py
uv run python -m evals.run_eval --verbose --trace-provider langfuse
```

Para workshop, use `--trace-provider local` quando cada grupo nao tiver credenciais Langfuse.
Use `--trace-provider langfuse` na maquina do facilitador, ou em um projeto Langfuse por grupo,
para mostrar traces, scores e comparacao entre runs.

## Setup com uv

```bash
uv sync
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
uv sync
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
uv run python -m evals.run_eval --verbose
```

Esse comando envia todas as perguntas do golden dataset e o contexto ficticio retornado pelas tools para Groq. Use apenas em ambiente aprovado para o workshop. Para registrar dataset, evaluators, traces e scores no Langfuse, siga a seção de observabilidade abaixo.

### Tools disponiveis para os agentes

- `search_policy_documents`: busca documentos de politica.
- `get_policy_by_id`: recupera uma politica especifica por id.
- `list_policy_versions`: lista versoes atuais e obsoletas.
- `calculate_reimbursement_deadline`: calcula prazo de reembolso.
- `validate_expense_receipt`: valida regra de recibo.
- `validate_transport_expense`: valida evidencias de taxi/app.
- `get_employee_profile`: retorna perfil ficticio para decisoes de privacidade.
- `get_salary_band`: retorna faixa salarial ficticia.
- `check_remote_work_eligibility`: checa home office internacional.
- `check_approval_matrix`: consulta regras de aprovacao.
- `check_software_vendor`: checa fornecedor de software.
- `get_password_reset_runbook`: busca runbook de reset/acesso.
- `get_device_inventory`: consulta inventario de equipamento.
- `create_support_ticket`: cria ticket simulado.

Algumas tools possuem regras ou caches propositalmente desatualizados. A expectativa do desafio e que os grupos identifiquem esses conflitos pela Evaluation, ajustem o sistema e expliquem o impacto para o cliente.

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

Para usar Langfuse no fluxo principal, primeiro configure as credenciais e suba o dataset/evaluators:

```bash
uv sync
cp .env.example .env
# preencha GROQ_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY e LANGFUSE_BASE_URL
uv run python scripts/setup_langfuse.py
```

O script cria no Langfuse:

- dataset `acme-agents-golden-dataset`;
- code evaluator `acme-json-contract`;
- code evaluator `acme-golden-dataset-rules`;
- code evaluator `acme-business-risk-flags`.
- evaluation rule ativa para JSON contract em observations;
- evaluation rule ativa para business risk flags em observations;
- evaluation rule ativa para golden dataset rules em experiments/dataset runs.

Se o Langfuse rejeitar o preflight de ativação via API, o script cria as rules desativadas e imprime um aviso. Nesse caso, teste e habilite as rules pela UI do Langfuse.

Para validar o setup sem criar nada:

```bash
uv run python scripts/setup_langfuse.py --dry-run
```

Depois rode a Evaluation enviando traces e scores para o Langfuse:

```bash
uv run python -m evals.run_eval --verbose --trace-provider langfuse
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

Nao comece alterando tudo. Rode a evaluation, olhe os piores casos, escolha uma classe de erro
e corrija uma coisa por vez.

## Fontes das integracoes

- Langfuse SDK: https://langfuse.com/docs/observability/sdk/overview
- Langfuse observation types: https://langfuse.com/docs/observability/features/observation-types
- Langfuse integrations: https://langfuse.com/integrations
- Langfuse Python reference: https://python.reference.langfuse.com/langfuse
- Groq + Agno: https://console.groq.com/docs/agno
- Groq tool use: https://console.groq.com/docs/tool-use
- Agno docs: https://docs.agno.com/
- uv: https://docs.astral.sh/uv/
