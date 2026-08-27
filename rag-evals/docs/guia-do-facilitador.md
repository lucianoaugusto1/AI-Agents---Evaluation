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
- `REMOVE_STOPWORDS_FROM_QUERY = False`: a pergunta vai crua para o BM25 e
  "qual", "para" e "posso" competem com os termos que importam. A lista
  `STOPWORDS` ja existe em `retriever.py` e nao e usada.
- `MAX_CONTEXT_CHARS = 420`: o contexto e cortado por numero de caracteres
  depois de concatenado, entao o ultimo chunk chega truncado no meio da frase.
- `STRICT_GROUNDING = False`: usa o prompt permissivo.

Codigo:

- `prompts.LOOSE_SYSTEM_PROMPT` manda complementar com conhecimento proprio e
  "nunca deixar o cliente sem resposta". Nao pede citacao nem recusa. O
  `STRICT_SYSTEM_PROMPT` correto ja esta no arquivo, so nao esta ligado.
- `pipeline.build_context` corta a string ja concatenada, sem verificar se
  cortou no meio de um chunk. `MAX_CONTEXT_CHARS` contorna o problema; cortar
  por chunk inteiro e a correcao de verdade, e fica como extensao opcional.
- `documents.split_text` corta por numero de caracteres. `CHUNK_SIZE` e
  `CHUNK_OVERLAP` resolvem na pratica; chunking por secao e a outra extensao
  opcional.

## Onde cada bug aparece

| Caso | O que o participante ve | Bug |
| --- | --- | --- |
| `REEMB-001` | contexto com 30 dias e 7 dias ao mesmo tempo; resposta cita o prazo revogado | documento obsoleto no indice |
| `REEMB-002` | recall 0.0: as duas vagas do top-k vao para `politica_reembolso_2023`, entao faltam os dois documentos esperados | top-k 2 + dois chunks do mesmo documento |
| `REEMB-003` | recall 0.0, vem `seguranca_conta` | query crua, sem stopwords |
| `PLANO-002` | os dois documentos certos sao recuperados e metade da resposta some | corte do contexto por caractere |
| `SLA-001` | a tabela de SLA chega partida | chunking de tamanho fixo |
| `FORA-001` | o modelo afirma ter certificacao que nao existe no corpus | sem limiar + prompt permissivo |
| `REEMB-001`, `REEMB-002` | as duas vagas do top-k com o mesmo documento | sem dedup |

## SEG-003: o teto que nenhum parametro alcanca

`SEG-003` fica em `recall 0.5` no baseline e continua em `recall 0.5` com as
sete correcoes aplicadas. Isso e proposital, mas nao esta no quadro de bugs
acima porque nao e um bug de configuracao: e o limite do BM25.

A pergunta diz "uma **sessao inativa expira**". O documento diz "**Sessoes
inativas expiram** em 12 horas". Sem stemming, `sessao` nao casa com `sessoes`,
`inativa` nao casa com `inativas` e `expira` nao casa com `expiram`. Os termos
que discriminam o documento certo nao produzem nenhum match, e
`seguranca_conta` cai para a ultima posicao do ranking, abaixo de todo o resto
do corpus. Para resgata-lo seria preciso `TOP_K = 8`, que derruba a precisao
em todos os outros casos.

Nao mande o grupo consertar. O valor didatico do caso e outro:

- ele mostra que existe falha de recuperacao que **nenhum ajuste de parametro
  resolve**, e que a resposta certa as vezes e trocar a tecnica de busca, nao
  girar o botao mais forte;
- ele e o gancho natural para embeddings e busca hibrida, que e exatamente o
  que um RAG de producao usaria e que este exercicio abre mao de proposito em
  favor da reprodutibilidade;
- ele treina a leitura honesta de eval: um caso que nao sobe nao e
  necessariamente um caso mal resolvido.

Se algum grupo diagnosticar sozinho que a causa e morfologia da query, isso
vale mais que qualquer ponto de score. A pergunta para devolver: "quanto voce
pagaria, em latencia e infra, para esse caso passar?"

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
6. `MIN_RELEVANCE_SCORE` acima de zero — descarta chunk irrelevante do
   contexto. Sozinho ele nao faz `FORA-001` recusar: mesmo com limiar em 0.5
   a pergunta de ISO 27001 ainda recupera `planos_assinatura` com score
   suficiente. Quem faz a recusa acontecer e o `STRICT_GROUNDING`; o limiar
   ajuda tirando ruido do prompt.
7. `REMOVE_STOPWORDS_FROM_QUERY = True`.

Todas as sete sao mudanca de parametro em `acme_cloud_rag/config.py`: da para
bater a meta sem escrever uma linha de logica. Quem terminar antes tem duas
extensoes opcionais, que exigem codigo e rendem uma apresentacao melhor:

- chunking por secao do Markdown, em vez de corte por numero de caracteres
  (`documents.split_text`);
- montagem de contexto que descarta o chunk inteiro quando ele nao cabe, em
  vez de cortar no meio da frase (`pipeline.build_context`).

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
- Por que `SEG-003` nao sobe com nenhum parametro, e o que isso diz sobre o
  limite da busca lexica?
- Quantas vezes o score subiu sem que o problema real tivesse sido resolvido?
- O que dessa suite voce colocaria para rodar em cada pull request?
