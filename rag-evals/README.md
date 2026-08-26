# Desafio de RAG — ACME Cloud

Segunda atividade do workshop de Evaluation. A primeira, na raiz do
repositorio, avalia um sistema de agentes. Esta avalia um **RAG**.

A ACME Cloud, empresa ficticia, tem um assistente de suporte ao cliente que
responde perguntas sobre reembolso, planos, seguranca, limites de API,
faturamento e SLA, consultando a propria base de documentos. Ele parece
funcionar em uma demo, mas cita politica revogada, corta o documento no meio,
inventa resposta quando nao encontra contexto e nao cita as fontes.

A ideia e a mesma da outra atividade:

> Voce nao consegue olhar uma resposta e decidir subjetivamente que ela "ficou
> boa". Voce precisa de uma suite de evals que separe a culpa do retriever da
> culpa do gerador.

## Arquitetura

```text
pergunta -> chunking -> indice BM25 -> top-k chunks -> contexto -> Groq -> JSON
                 |                          |                        |
          Context Recall          Context Precision      Faithfulness / Relevancy / Format
```

```text
rag-evals/
├── data/documents/*.md          base de conhecimento da ACME Cloud
├── src/rag_evals/config.py      os parametros que o desafio pede para ajustar
├── src/rag_evals/documents.py   carga do corpus e chunking
├── src/rag_evals/retriever.py   BM25 puro, sem servico externo
├── src/rag_evals/prompts.py     prompts do gerador
├── src/rag_evals/pipeline.py    recuperacao -> contexto -> geracao
├── evals/golden_dataset.jsonl   16 casos rotulados
├── evals/metrics.py             context precision e recall (deterministicos)
├── evals/judge.py               LLM-as-a-Judge + contrato de saida
├── evals/observability.py       traces none / local / Langfuse
└── scripts/                     ask.py, run_eval.py, setup_langfuse.py
```

O retriever e BM25 de verdade, implementado em Python, sem vector store nem
servico externo: o ranking e identico em todas as maquinas do workshop, entao
a discussao fica sobre o diagnostico e nao sobre "aqui deu diferente". A
geracao e a avaliacao usam IA real via Groq.

## Setup

O setup e o mesmo da atividade de agentes. Na raiz do repositorio:

```bash
uv sync
cp .env.example .env
# preencha GROQ_API_KEY
```

## Como rodar

Uma pergunta, mostrando os chunks recuperados e o contexto que foi para o
modelo:

```bash
uv run python rag-evals/scripts/ask.py "Qual e o prazo para pedir reembolso do plano Anual?"
```

A suite completa:

```bash
uv run python rag-evals/scripts/run_eval.py
uv run python rag-evals/scripts/run_eval.py --verbose
uv run python rag-evals/scripts/run_eval.py --case REEMB-002 --verbose
uv run python rag-evals/scripts/run_eval.py --json
```

Os testes deterministicos, que nao consomem chave nenhuma:

```bash
cd rag-evals && uv run python -m unittest discover -s tests -t .
```

## Metricas

| Metrica | O que mede | Culpa quem | Como e calculada |
| --- | --- | --- | --- |
| **Context Precision** | Os documentos certos aparecem, e no topo? | Retriever (ranking) | Deterministica |
| **Context Recall** | A recuperacao trouxe tudo que a resposta precisa? | Retriever (cobertura) | Deterministica |
| **Faithfulness** | Toda afirmacao esta sustentada pelo contexto? | Gerador (ancoragem) | LLM-as-a-Judge |
| **Answer Relevancy** | A resposta responde a pergunta? | Gerador (utilidade) | LLM-as-a-Judge |
| **Format** | JSON valido, citacoes validas, recusa correta | Contrato | Deterministica |

Context Precision e o *Average Precision* dos documentos recuperados:

```text
AP = (1 / |esperados|) * soma de P@i nas posicoes i relevantes
```

Ela e sensivel a ordem — o documento certo em primeiro vale 1.0, em terceiro
vale 0.33 — e nao pune por si so o simples aumento do top-k.

Faithfulness tem um piso deterministico por cima do juiz: se a resposta contem
uma das `forbidden_claims` do caso (por exemplo o prazo da politica revogada),
a nota vai a zero independentemente do que o juiz achou. Numero errado de
politica interna nao e questao de opiniao.

Score final:

```text
30% faithfulness + 20% answer relevancy + 20% context recall
+ 15% context precision + 15% format
```

## Objetivo do desafio

Subir o score sem editar o dataset nem o avaliador.

Pode alterar:

- `src/rag_evals/config.py`
- `src/rag_evals/documents.py`
- `src/rag_evals/retriever.py`
- `src/rag_evals/prompts.py`
- `src/rag_evals/pipeline.py`

Nao pode alterar:

- `evals/golden_dataset.jsonl`
- `evals/metrics.py`
- `evals/judge.py`
- `evals/run_eval.py`

Meta: `0.85+`. O score inicial varia entre execucoes porque a geracao e a
avaliacao usam IA real — registre o primeiro resultado antes de mexer em
qualquer coisa.

## Por onde comecar

Rode a suite, escolha o pior caso e olhe o trace antes de mudar codigo. As
perguntas que costumam abrir o diagnostico:

```text
O documento certo foi recuperado?           -> se nao, e retriever
O trecho certo estava dentro do chunk?      -> se nao, e chunking
O trecho sobreviveu ao corte do contexto?   -> se nao, e montagem de contexto
O modelo respondeu so com o que recebeu?    -> se nao, e prompt
```

Comece por `--case REEMB-001 --verbose`: os dois documentos de reembolso
entram no contexto, um dizendo 30 dias e o outro, revogado desde 2025, dizendo
7 dias. Depois `--case PLANO-002 --verbose`: os dois documentos certos sao
recuperados e mesmo assim metade da resposta nao aparece.

Nao mexa em tudo de uma vez. Corrija uma classe de erro, rode a suite de novo
e anote o efeito em cada metrica — inclusive quando o efeito for negativo.

## Observabilidade com Langfuse

Cada caso vira um trace com dois spans filhos:

```text
rag-eval:REEMB-001
├── retrieve    chunks recuperados, score de cada um, flag de obsoleto
├── generate    prompt montado e resposta bruta do modelo
└── scores      overall, context precision/recall, faithfulness, relevancy, format
```

E onde da para ver, sem ler codigo, que chunk entrou no prompt e por que a
resposta saiu errada.

Sem conta Langfuse, o mesmo conteudo vai para um arquivo JSONL:

```bash
uv run python rag-evals/scripts/run_eval.py --verbose --trace-provider local
# grava em rag-evals/runs/
```

Com Langfuse, preencha `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e
`LANGFUSE_BASE_URL` no `.env` da raiz e suba o dataset e os evaluators:

```bash
uv run python rag-evals/scripts/setup_langfuse.py --dry-run   # valida sem criar
uv run python rag-evals/scripts/setup_langfuse.py
uv run python rag-evals/scripts/run_eval.py --verbose --trace-provider langfuse
```

O script cria o dataset `acme-cloud-rag-golden-dataset` e tres code evaluators:
`rag-json-contract`, `rag-grounding-rules` e `rag-retrieval-quality`. Eles sao
deterministicos e rodam dentro do Langfuse, sobre os traces.

## Entrega

```text
Grupo:
Score inicial:
Score final:

Falha 1:
Evidencia (caso e trace):
Correcao:

Falha 2:
Evidencia (caso e trace):
Correcao:

Falha 3:
Evidencia (caso e trace):
Correcao:

Risco restante:
```

Nao basta subir o score por tentativa e erro: a entrega precisa ligar falha,
evidencia e correcao.

## Limitacoes assumidas

- Recuperacao lexica (BM25), sem embeddings. Um RAG de producao usaria busca
  vetorial ou hibrida; aqui a escolha e por reprodutibilidade na sala.
- Dataset pequeno (16 casos) e rotulado a mao, que e exatamente a cara do
  primeiro eval set de um projeto real.
- O juiz e um LLM: ele varia entre execucoes. Por isso as metricas de
  recuperacao e o contrato de saida sao deterministicos, e as afirmacoes
  proibidas sao checadas por regra.
