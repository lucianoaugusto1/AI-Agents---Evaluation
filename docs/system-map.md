# Mapa do sistema

```text
Pergunta do usuario
        |
        v
orchestrator.route()
        |
        +--> finance_agent()
        +--> hr_agent()
        +--> it_agent()
        +--> general_agent()
        |
        v
knowledge_base.retrieve()
        |
        v
Resposta JSON esperada
```

## Contrato esperado de resposta

```json
{
  "answer": "texto final para o usuario",
  "citations": ["finance_current"],
  "confidence": "low | medium | high",
  "escalate": true
}
```

## Evaluation

```text
golden_dataset.jsonl -> run_eval.py -> judge.py -> score -> observability
                                                        |
                                                        +--> local JSONL
                                                        +--> Langfuse
```

O avaliador nao tenta ser perfeito. Ele e propositalmente simples para deixar claro o mecanismo de avaliação:

- presença de conteudo esperado;
- ausencia de claims proibidas;
- citacoes obrigatorias;
- formato JSON;
- decisao de escalacao.

## API

```text
FastAPI
  |
  +--> POST /ask
  |       |
  |       +--> answer_question()
  |
  +--> POST /eval/run
          |
          +--> evals.run_eval.run()
```
