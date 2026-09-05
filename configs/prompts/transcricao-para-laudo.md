# Prompt — Transcrição de consulta → SOAP → Laudo

Uso: depois da transcrição realtime (tutorial 05) ou de arquivo
(tutorial 06). Rode em DUAS chamadas (mais confiável que uma só).

## Chamada 1 — Nota SOAP

### System

```text
Você documenta consultas médicas em nota SOAP concisa, português técnico.
Não adicione informações ausentes na transcrição; interprete siglas
clínicas óbvias (AV = acuidade visual, PIO = pressão intraocular).
```

### User (modelo)

```text
Transcrição diarizada de consulta. SPEAKER 1 = MÉDICO, SPEAKER 2 = PACIENTE.
Consolide em SOAP (Subjetivo, Objetivo, Avaliação, Plano). Corrija erros
óbvios de transcrição de termos médicos; mantenha dados numéricos exatamente
como ditados.

TRANSCRIÇÃO:
{{transcricao}}
```

## Chamada 2 — Laudo a partir da SOAP

System: o de [`laudo-oftalmologia.md`](laudo-oftalmologia.md).
User: cole a nota SOAP gerada na chamada 1 + dados de identificação
disponíveis.

## Observações

- Se a diarização trocar os papéis, inverta a instrução de SPEAKER e
  refaça a SOAP antes do laudo (barato: use `lapan/qwen3:8b` para validar).
- Áudios >40 min: fatie a transcrição em blocos por tópico e gere uma SOAP
  por bloco antes de consolidar.
