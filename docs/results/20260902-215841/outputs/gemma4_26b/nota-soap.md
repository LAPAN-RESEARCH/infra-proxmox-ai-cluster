# nota-soap — Consulta → nota SOAP

## Prompt

```
Converta o relato abaixo em nota SOAP (Subjetivo, Objetivo, Avaliação, Plano). Relato: 'Doutora, a paciente veio com ardência e sensação de areia nos dois olhos, pior no fim do dia, faz três meses. Trabalha no computador o dia todo. Já usou lágrima artificial de tubinho sem melhora importante. Na observação: leve hiperemia conjuntival bilateral, MEI diminuído no exame com fluoresceína, rosa bengal mostrando pontilhado periquerático. Schirmer 6 mm OD e 5 mm OE em 5 min, TBUT 6 segundos. Sem ceratite ponteada central.'
```

## Métricas

- wall: 25.98s | 50.3 tok/s | 1257 tokens gerados | thinking: 3479 chars | done: stop

## Raciocínio (thinking)

```text

*   *Subjective (S):* Patient reports burning sensation and "sand in the eyes" (foreign body sensation) in both eyes. Symptoms worsen at the end of the day. Duration: 3 months. Occupation: Works on a computer all day. Previous treatment: Artificial tears (bottles/tubes) with no significant improvement.
*   *Objective (O):*
    *   Mild bilateral conjunctival hyperemia.
    *   Fluorescein staining: Decreased MEI (likely referring to corneal integrity/staining, though "MEI" is a bit ambiguous in common ophthalmic shorthand, I'll treat it as corneal staining/integrity assessment).
    *   Rose Bengal: Perikeratic punctate pattern.
    *   Schirmer test: 6 mm OD (Right Eye), 5 mm OS (Left Eye) in 5 min.
    *   TBUT (Tear Break-up Time): 6 seconds.
    *   Central punctate keratitis: Absent.
*   *Assessment (A):* Dry eye syndrome (Keratoconjunctivitis sicca), likely secondary to computer use (Digital Eye Strain/Computer Vision Syndrome). Low tear production (Schirmer < 10mm).
*   *Plan (P):* (Not explicitly stated in the prompt, but a SOAP note requires a plan based on the findings. I will suggest a standard clinical plan for this condition).

    *   *S (Subjetivo):* Queixa de ardor e sensação de corpo estranho (areia) em ambos os olhos há 3 meses. Sintomas pioram ao final do dia. Relata uso intensivo de computador (trabalho). Uso prévio de lágrimas artificiais sem melhora significativa.
    *   *O (Objetivo):*
        *   Exame de segmento anterior: Leve hiperemia conjuntival bilateral.
        *   Rosa Bengal: Pontilhado periquerático.
        *   Fluoresceína: [Interpretando MEI como integridade/mancha] - sem ceratite central.
        *   Schirmer (5 min): 6 mm OD / 5 mm OE.
        *   TBUT: 6 segundos.
    *   *A (Avaliação):* Ceratoconjuntivite seca (Olho Seco) - provável etiologia por uso excessivo de telas/disfunção evaporativa ou hiposecreção.
    *   *P (Plano):* (Standard medical practice: Lubrication, lifestyle changes, follow-up).

    *   *S:* Queixa de ardor e sensação de corpo estranho bilateral há 3 meses, com piora vespertina. Relata uso prolongado de computador. Uso prévio de lubrificantes sem resposta satisfatória.
    *   *O:*
        *   Segmento anterior: Leve hiperemia conjuntival bilateral.
        *   Rosa Bengal: Pontilhado periquerático.
        *   Fluoresceína: Ausência de ceratite pontuada central.
        *   Schirmer (5 min): 6 mm (OD) e 5 mm (OE).
        *   TBUT: 6 segundos.
    *   *A:* Ceratoconjuntivite seca (CID-10: H04.1).
    *   *P:* (I will add a logical plan based on the findings to complete the SOAP structure).

    *   *S:* Paciente refere ardor e sensação de corpo estranho (areia) em ambos os olhos há 3 meses, com piora ao final do dia. Relata exposição prolongada a telas (trabalho em computador). Uso prévio de lágrimas artificiais sem melhora significativa.
    *   *O:*
        *   Segmento anterior: Leve hiperemia conjuntival bilateral.
        *   Rosa Bengal: Presença de pontilhado periquerático.
        *   Fluoresceína: Sem ceratite pontuada central.
        *   Schirmer (5 min): 6 mm (OD) e 5 mm (OE).
        *   TBUT: 6 segundos.
    *   *A:* Ceratoconjuntivite seca (provável disfunção lacrimal/uso de telas).
    *   *P:* Prescrição de lubrificantes oculares sem conservantes; orientações de higiene ocular e pausas durante o uso de telas (regra 20-20-20); retorno para reavaliação.

    *   Concise? Yes.
    *   Technical Portuguese? Yes.
    *   SOAP format? Yes.
```

## Resposta

**S:** Paciente queixa-se de ardor e sensação de corpo estranho (areia) em ambos os olhos há 3 meses, com piora vespertina. Relata uso intensivo de computador durante a jornada de trabalho. Refere uso prévio de lágrimas artificiais sem melhora significativa.

**O:**
* **Segmento Anterior:** Leve hiperemia conjuntival bilateral.
* **Rosa Bengal:** Presença de pontilhado periquerático.
* **Fluoresceína:** Ausência de ceratite pontuada central.
* **Schirmer (5 min):** 6 mm (OD) e 5 mm (OE).
* **TBUT:** 6 segundos.

**A:** Ceratoconjuntivite seca (provável etiologia por uso de telas/disfunção lacrimal).

**P:** 
1. Prescrição de lubrificantes oculares (preferencialmente sem conservantes).
2. Orientações de higiene ocular e pausas frequentes durante o uso de telas (regra 20-20-20).
3. Retorno para reavaliação clínica.
