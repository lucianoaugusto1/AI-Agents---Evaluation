# ACME Agents Eval Challenge

Projeto didatico para workshop de Evaluation em sistemas com LLM.

A ACME Corp tem um assistente interno com agentes especializados em RH, Financeiro e TI. O sistema parece funcionar em demos simples, mas tem bugs intencionais: usa politica antiga, inventa respostas sem contexto, ignora formato, vaza instrucao interna e falha em casos ambíguos.

O desafio dos participantes e usar Evaluation para diagnosticar e corrigir o sistema.

## Objetivo

Melhorar o score do sistema sem editar o dataset ou o avaliador.

Arquivos que podem ser alterados durante o desafio:

- `src/acme_support_ai/agents.py`
- `src/acme_support_ai/orchestrator.py`
- `src/acme_support_ai/knowledge_base.py`
- `src/acme_support_ai/policies/*.md`

Arquivos que representam a suite de evaluation e nao devem ser editados:

- `evals/golden_dataset.jsonl`
- `evals/judge.py`
- `evals/run_eval.py`

## Como rodar

```bash
python3 -m evals.run_eval
```

Para ver detalhes caso a caso:

```bash
python3 -m evals.run_eval --verbose
```

Para rodar os testes da estrutura do projeto:

```bash
python3 -m unittest discover
```

Para testar uma pergunta manual:

```bash
python3 -m src.acme_support_ai.cli "Qual e o prazo para pedir reembolso de viagem?"
```

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

- Baseline esperado: abaixo de `0.70`
- Meta do desafio: `0.85+`
- Vitoria tecnica: melhorar score e explicar quais problemas foram encontrados

## Entrega dos grupos

Cada grupo deve enviar:

- Score inicial
- Score final
- 3 principais falhas encontradas
- Mudancas feitas
- 1 teste que ainda falha ou risco restante

## Dica

Nao comece alterando tudo. Rode a evaluation, olhe os piores casos e corrija uma classe de erro por vez.
