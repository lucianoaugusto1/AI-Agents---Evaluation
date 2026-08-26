# Guia do facilitador — desafio de RAG

Nao distribua este arquivo antes do exercicio: ele lista os bugs plantados.

## Historia

A ACME Cloud tem um assistente de suporte com RAG sobre a propria base de
documentos. A demo parece boa. A evaluation mostra que ele cita politica
revogada, perde metade da resposta em perguntas de dois documentos e inventa
quando nao encontra contexto.

## Bugs plantados

Configuracao (`acme_cloud_rag/config.py`):

- `CHUNK_SIZE = 320` com `CHUNK_OVERLAP = 0`: corte de tamanho fixo, sem
  respeitar paragrafo, titulo ou linha de tabela. Um trecho relevante pode
  ficar partido entre dois chunks e nenhum responder sozinho.
- `FILTER_OBSOLETE_DOCUMENTS = False`: `politica_reembolso_2023.md` esta
  marcado como obsoleto no proprio corpo e mesmo assim entra no indice.
- `TOP_K = 2`: nao cabem dois documentos distintos nas perguntas de duas
  fontes.
- `MIN_RELEVANCE_SCORE = 0.0`: nao existe o caso "nao encontrei contexto util",
  entao o modelo sempre recebe algo e sempre responde alguma coisa.
- `DEDUPE_BY_DOCUMENT = False`: dois chunks do mesmo documento ocupam as duas
  vagas do top-k e o segundo documento nunca chega.
- `MAX_CONTEXT_CHARS = 700`: o contexto e cortado por numero de caracteres
  depois de concatenado, entao o ultimo chunk chega truncado no meio da frase.
- `STRICT_GROUNDING = False`: usa o prompt permissivo.

Codigo:

- `prompts.LOOSE_SYSTEM_PROMPT` manda complementar com conhecimento proprio e
  "nunca deixar o cliente sem resposta". Nao pede citacao nem recusa. O
  `STRICT_SYSTEM_PROMPT` correto ja esta no arquivo, so nao esta ligado.
- `retriever.normalize_query` manda a pergunta crua para o BM25: a lista
  `STOPWORDS` existe e nao e usada, entao "qual", "para", "posso" competem com
  os termos que importam.
- `pipeline.build_context` corta a string ja concatenada, sem verificar se
  cortou no meio de um chunk.

## Onde cada bug aparece

| Caso | O que o participante ve | Bug |
| --- | --- | --- |
| `REEMB-001` | contexto com 30 dias e 7 dias ao mesmo tempo; resposta cita o prazo revogado | documento obsoleto no indice |
| `REEMB-002` | recall 0.5, falta `planos_assinatura` | top-k 2 + dois chunks do mesmo documento |
| `REEMB-003` | recall 0.0, vem `seguranca_conta` | query crua, sem stopwords |
| `PLANO-002` | os dois documentos certos sao recuperados e metade da resposta some | corte do contexto por caractere |
| `SLA-001` | a tabela de SLA chega partida | chunking de tamanho fixo |
| `FORA-001` | o modelo afirma ter certificacao que nao existe no corpus | sem limiar + prompt permissivo |
| `API-001`, `RET-001` | as duas vagas do top-k com o mesmo documento | sem dedup |

## Correcoes esperadas

Nao existe uma resposta unica. As mudancas que costumam levar a meta:

1. `FILTER_OBSOLETE_DOCUMENTS = True` — resolve a classe mais grave, que e
   responder com politica revogada.
2. `STRICT_GROUNDING = True` — o modelo passa a citar e a recusar.
3. `TOP_K = 4` com `DEDUPE_BY_DOCUMENT = True` — resolve as perguntas de dois
   documentos.
4. `CHUNK_SIZE = 700` com `CHUNK_OVERLAP = 150`, ou chunking por secao —
   mantem a tabela e o paragrafo inteiros.
5. `MAX_CONTEXT_CHARS` maior, ou corte por chunk em vez de por caractere.
6. `MIN_RELEVANCE_SCORE` acima de zero — habilita a recusa de `FORA-001`.
7. Remover stopwords em `normalize_query`.

Vale provocar o trade-off: subir `TOP_K` sem dedup nao resolve, e subir demais
derruba a precisao e enche o prompt de ruido, que em producao custa token,
latencia e ancoragem.

## Como conduzir

1. Todos rodam `uv sync` e preenchem `GROQ_API_KEY`.
2. Todos rodam `uv run python rag-evals/scripts/run_eval.py --verbose` e
   **anotam o score inicial** antes de mexer em qualquer coisa.
3. Cinco minutos so lendo os piores casos, sem editar codigo.
4. Cada grupo escolhe uma classe de erro por vez e roda a suite de novo.
5. Na maquina do facilitador, rode com `--trace-provider langfuse` e mostre o
   span `retrieve` do caso `REEMB-001`: os dois documentos de reembolso lado a
   lado, um deles marcado como obsoleto.
6. No fim, cada grupo apresenta score antes/depois e o diagnostico.

## Perguntas para fechar a discussao

- Qual metrica melhorou e qual piorou na mesma mudanca?
- Quantas vezes o score subiu sem que o problema real tivesse sido resolvido?
- O que dessa suite voce colocaria para rodar em cada pull request?
