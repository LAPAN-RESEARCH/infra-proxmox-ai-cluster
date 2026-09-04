# nota-soap — Consulta → nota SOAP

## Prompt

```
Converta o relato abaixo em nota SOAP (Subjetivo, Objetivo, Avaliação, Plano). Relato: 'Doutora, a paciente veio com ardência e sensação de areia nos dois olhos, pior no fim do dia, faz três meses. Trabalha no computador o dia todo. Já usou lágrima artificial de tubinho sem melhora importante. Na observação: leve hiperemia conjuntival bilateral, MEI diminuído no exame com fluoresceína, rosa bengal mostrando pontilhado periquerático. Schirmer 6 mm OD e 5 mm OE em 5 min, TBUT 6 segundos. Sem ceratite ponteada central.'
```

## Métricas

- wall: 126.17s | 7.5 tok/s | 923 tokens gerados | thinking: 2286 chars | done: stop

## Raciocínio (thinking)

```text
The user wants me to convert a clinical narrative into a SOAP note (Subjective, Objective, Assessment, Plan) in concise technical Portuguese. Let me analyze the information:

**Subjective (S):**
- Patient complains of burning and sand sensation in both eyes
- Worse at end of day
- Duration: 3 months
- Works at computer all day (occupational risk factor)
- Previous treatment: artificial tears (tube) without significant improvement

**Objective (O):**
- Bilateral mild conjunctival hyperemia
- Decreased MEI (Menisco de Lágrima / Tear Meniscus) on fluorescein exam
- Rose bengal: punctate perikeratic staining
- Schirmer: 6 mm OD and 5 mm OE in 5 min
- TBUT: 6 seconds
- No central punctate keratitis

**Assessment (A):**
- Dry eye syndrome (Síndrome do Olho Seco) - bilateral
- Mild to moderate (Schirmer <10 mm, TBUT <10s, rose bengal positive)
- Evaporative component likely (TBUT 6s suggests tear film instability)
- Occupational factor (computer use)
- Refractory to simple artificial tears

**Plan (P):**
The narrative doesn't explicitly state a plan, but I should note that the plan isn't specified in the report. I'll indicate that the plan is not detailed in the narrative, or I can suggest standard next steps. Actually, the user just asked me to convert the narrative into SOAP format. The narrative doesn't include a plan. I'll note that the plan is not specified in the narrative, or I'll leave it as "a definir" or note it's not provided. Let me re-read...

The narrative ends with "Sem ceratite ponteada central." - there's no plan mentioned. I'll indicate the plan is not specified in the narrative, or I could suggest a reasonable plan based on the findings. Since the user asked me to convert the narrative, I should stick to what's given. I'll note "Plano não especificado no relato" or I could suggest a standard plan. Let me just note it's not provided and perhaps suggest what would be appropriate.

Actually, looking again, the user said "Converta o relato abaixo em nota SOAP" - so I should format what's there. For the Plan, since it's not in the narrative, I'll note it's not specified. But to be helpful, I might add a brief suggested plan based on standard practice. Let me keep it concise and technical.

Let me write this in concise technical Portuguese.
```

## Resposta

# Nota SOAP

**S – Subjetivo**
Paciente refere ardência e sensação de "areia" em ambos os olhos, há 3 meses, com piora vespertina. Exposição ocupacional a tela de computador em tempo integral. Previa uso de lágrima artificial (tubinho) sem melhora relevante.

**O – Objetivo**
- Hiperemia conjuntival bilateral, leve.
- MEI diminuído (fluoresceína).
- Rosa bengal: pontilhado periquerático bilateral.
- Schirmer (5 min): 6 mm OD / 5 mm OE.
- TBUT: 6 s.
- Sem ceratite ponteada central.

**A – Avaliação**
Síndrome do olho seco bilateral, grau leve–moderado, com componente evaporativo predominante (TBUT < 10 s, Schirmer < 10 mm, estase periquerática). Fator agravante ocupacional (uso prolongado de tela). Refratária a lágrima artificial simples.

**P – Plano**
*(Não explicitado no relato. Sugestão condicional:)*
- Lágrima artificial sem conservante (gotas ou gel noturno), 4×/dia.
- Pausas visuais (regra 20-20-20) e aumento de piscadas.
- Reavaliação em 4 semanas; se persistência → considerar ciclosporina 0,1 % ou lipídios tópicos; descartar componente inflamatório com OCT de pálpebra / meibografia.
- Orientar hidratação e evitar ar-condicionado direcionado.
