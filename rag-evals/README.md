# RAG Evals Workshop

Parte 2 do workshop de Evaluation. A parte de agentes fica na raiz do
repositorio; esta atividade e independente e roda a partir desta pasta.

A tiny RAG system plus a full evaluation pipeline, built for a **20-minute
individual hands-on activity**.

The point of the activity:

> You cannot look at one answer and decide subjectively that it "looks good".
> You need a reproducible set of evals.

Everything runs **offline and deterministically** by default: no Docker, no
database, no vector store, no API key required.

---

## Setup

```bash
git clone https://github.com/lucianoaugusto1/AI-Agents---Evaluation.git
cd AI-Agents---Evaluation/rag-evals

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

With `uv` instead:

```bash
uv venv && source .venv/bin/activate
uv pip install -r requirements.txt
```

Optional (only to enable LLM-as-a-Judge):

```bash
cp .env.example .env             # then fill OPENAI_API_KEY
```

## Quick start

```bash
python scripts/run_rag.py                       # see the pipeline answer one question
python scripts/evaluate.py                      # score the whole dataset
python scripts/evaluate.py --save-baseline      # store the current scores
python scripts/evaluate.py --compare-baseline   # compare after changing config
python scripts/regression.py                    # PASS / FAIL against thresholds
pytest                                          # unit tests
```

Useful flags: `--case <id>` (one test case), `--quiet` (summary table only),
`--top-k N` (override TOP_K without editing the file).

---

## Architecture

```text
Question → Retriever (BM25) → Top-K documents → Generator → Answer
                    │                                 │
              Context Precision                  Faithfulness
              Context Recall                     Answer Relevancy
```

```text
rag-evals/
├── data/documents/*.md      knowledge base (fictional SaaS docs, 1 file = 1 chunk)
├── data/eval_dataset.json   10 test cases with expected relevant documents
├── src/config.py            TOP_K and STRICT_CONTEXT_PROMPT — the two knobs
├── src/retriever.py         pure-python BM25, no embeddings, no service
├── src/generator.py         local extractive generator (or OpenAI, if configured)
├── src/evals/               one file per metric + the judge abstraction
├── scripts/                 run_rag.py, evaluate.py, regression.py
└── thresholds.yaml          regression thresholds
```

The retriever returns whole documents, so a "retrieved chunk" is simply a
document id such as `refund_policy`. That keeps the eval output readable.

---

## Metrics

| Metric | What it measures | Which part of the RAG | How it is computed here |
| --- | --- | --- | --- |
| **Context Precision** | Are the retrieved documents relevant, and do the relevant ones come first? | Retriever (ranking) | **Deterministic** |
| **Context Recall** | Did retrieval bring back everything the answer needs? | Retriever (coverage) | **Deterministic** |
| **Faithfulness** | Is every claim in the answer supported by the retrieved context? | Generator (grounding) | Local judge **or** LLM-as-a-Judge |
| **Answer Relevancy** | Does the answer actually answer the question, without padding? | Generator (usefulness) | Local judge **or** LLM-as-a-Judge |

### Context Precision — deterministic

```text
Context Precision = (1/K) * Σ_{i=1..K} Precision@i
Precision@i       = relevant documents among the first i / i
```

A document is relevant when its id appears in `expected_relevant_document_ids`.
The formula is **order aware** (rank 1 contributes to every term, rank 5 to
almost nothing) and **noise aware** (each extra irrelevant document drags the
mean down). Plain `relevant / retrieved` would ignore ranking entirely.

### Context Recall — deterministic

```text
Context Recall = expected documents retrieved / expected documents
```

Multi-document test cases are the ones that expose low recall.

### Faithfulness — LLM-as-a-Judge (or local fallback)

```text
Faithfulness = supported claims / total claims
```

Each sentence of the answer is a claim. The local judge marks a claim
supported when ≥75% of its content words appear in the retrieved context; the
OpenAI judge extracts the claims and judges each one, returning a short
justification and the unsupported claims. The rubric is the same prompt in
both cases (`src/evals/faithfulness.py`).

### Answer Relevancy — LLM-as-a-Judge (or local fallback)

```text
Answer Relevancy = 0.5 * coverage + 0.5 * focus

coverage = question keywords present in the answer / question keywords
focus    = answer sentences that are on topic / answer sentences
```

`coverage` punishes dodging the question, `focus` punishes padding. As in
RAGAS, a non-committal answer ("not enough information") scores **0** — it can
be perfectly faithful and still not help the user. That is a real trade-off,
not a bug.

### Deterministic vs LLM — read this

| Mode | When | Faithfulness / Answer Relevancy |
| --- | --- | --- |
| `local` (default) | no `OPENAI_API_KEY` | deterministic word-overlap judge |
| `openai` | `OPENAI_API_KEY` set in `.env` | real LLM-as-a-Judge |

Set `EVAL_MODE` in `.env` to `local`, `openai` or `auto` (default: use the LLM
if a key exists, otherwise fall back). **Context Precision and Context Recall
never use an LLM** — they are always computed from the dataset. If an LLM call
fails, the local judge takes over and prints a warning, so a flaky network
never breaks the workshop.

---

## Workshop exercise — 20 minutes

Everything below is **individual**. You do not need anyone else.

### Part 1 — Baseline (3 min)

```bash
python scripts/evaluate.py --save-baseline
```

Look at the four averages and answer for yourself:

```text
Which metric has the lowest score?
Is the main problem retrieval or generation?
```

Hint: the first two metrics only blame the retriever, the last two only blame
the generator.

### Part 2 — Investigate one case (4 min)

```bash
python scripts/evaluate.py --case refund-002
```

Look at: expected documents, retrieved documents, the generated answer, the
four scores. Then answer:

```text
Why did this case receive this score?
```

(You should see `pricing_faq` — a decoy document — ranked first, and one of the
two expected documents missing.) Try `--case hallucination-001` too: the
context does not answer the question and the generator invents something.

### Part 3 — Change TOP_K (5 min)

Edit `src/config.py`:

```python
TOP_K = 2   →   TOP_K = 5
```

```bash
python scripts/evaluate.py --compare-baseline
```

```text
Which metric improved?   Which metric got worse?   Why?
```

Expected shape of the result: **Context Recall goes up, Context Precision goes
down**. More context is not automatically better — you also retrieved more
noise, and in a real system that noise costs tokens, latency and grounding.

### Part 4 — Faithfulness experiment (4 min)

Put `TOP_K` back to `2`, then edit `src/config.py`:

```python
STRICT_CONTEXT_PROMPT = False   →   STRICT_CONTEXT_PROMPT = True
```

```bash
python scripts/evaluate.py --compare-baseline
```

```text
Did Faithfulness improve?   Did any other metric change?   Why?
```

With a real LLM this changes the system prompt (answer only from the context,
admit when information is missing). In deterministic local mode the equivalent
happens in `LocalGenerator`: the strict generator only keeps sentences that are
really on topic and replies "not enough information" instead of inventing an
answer. Retrieval metrics do not move at all — you changed the generator, not
the retriever.

### Part 5 — Regression test (4 min)

```bash
python scripts/regression.py     # expect PASS with the default config
echo $?                          # 0
```

Now break it on purpose (for example `TOP_K = 5`, or `TOP_K = 1`) and run it
again:

```bash
python scripts/regression.py
echo $?                          # 1
```

You get the failing metric, the threshold and the actual value. Thresholds live
in `thresholds.yaml`.

```text
This same command could run on every pull request.
```

It already does: `.github/workflows/evals.yml` installs the dependencies, runs
`pytest` and then `python scripts/regression.py`. Because the exit code is 1 on
failure, the PR is blocked — exactly like a traditional regression test suite,
except the thing being protected is answer quality. CI runs with
`EVAL_MODE=local`, so it costs nothing and never flakes on an external API.

---

## Reference: the two knobs

`src/config.py`

```python
TOP_K = 2                      # how many documents the retriever returns
STRICT_CONTEXT_PROMPT = False  # how the generator is allowed to answer
```

## Limitations (on purpose)

* One document = one chunk. Real systems chunk and embed; here BM25 keeps the
  output readable and reproducible.
* The local judge uses word overlap, not semantics. It is a stand-in that makes
  the *pipeline* demonstrable without an API key — a real project should use an
  LLM judge (or human labels) for Faithfulness and Answer Relevancy.
* The dataset is small (10 cases) and hand-labelled, which is exactly what a
  first eval set looks like in practice.
