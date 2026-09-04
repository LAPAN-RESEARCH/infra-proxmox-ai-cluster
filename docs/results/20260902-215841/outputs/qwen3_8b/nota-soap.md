# nota-soap — Consulta → nota SOAP

## Prompt

```
Converta o relato abaixo em nota SOAP (Subjetivo, Objetivo, Avaliação, Plano). Relato: 'Doutora, a paciente veio com ardência e sensação de areia nos dois olhos, pior no fim do dia, faz três meses. Trabalha no computador o dia todo. Já usou lágrima artificial de tubinho sem melhora importante. Na observação: leve hiperemia conjuntival bilateral, MEI diminuído no exame com fluoresceína, rosa bengal mostrando pontilhado periquerático. Schirmer 6 mm OD e 5 mm OE em 5 min, TBUT 6 segundos. Sem ceratite ponteada central.'
```

## Métricas

- wall: 12.25s | 74.0 tok/s | 892 tokens gerados | thinking: 2061 chars | done: stop

## Raciocínio (thinking)

```text
Okay, I need to convert the given clinical report into a SOAP note. Let me start by recalling what each section of SOAP entails. 

Subjective (S): This is where the patient's own symptoms and concerns are documented. The patient mentioned burning and a sandy sensation in both eyes, worse in the evening, for three months. She works on a computer all day. She tried artificial tears without significant improvement. 

Objective (O): Here, the physical exam findings and test results go. The report mentions mild bilateral conjunctival hyperemia, decreased MEI with fluorescein, rose bengal showing punctate epithelial changes. Schirmer test results are 6 mm OD and 5 mm OE after 5 minutes. TBUT is 6 seconds. No central punctate keratitis. 

Assessment (A): The possible diagnosis based on the findings. The symptoms and signs point towards dry eye syndrome, specifically evaporative dry eye given the computer use and Schirmer results. The TBUT is low, which is a key indicator. The fluorescein and rose bengal tests show epithelial changes, which are typical in dry eye. 

Plan (P): The treatment and follow-up. The patient should continue using artificial tears, maybe switch to a preservative-free version. Recommend a warm compress and lid hygiene. Maybe a referral to an ophthalmologist for further evaluation. Also, suggest using a humidifier and taking breaks from the computer. 

Wait, I should make sure all the objective findings are included. The Schirmer test is 6 mm OD and 5 mm OE, which is below normal. TBUT is 6 seconds, which is also low. The fluorescein and rose bengal tests show punctate changes. No central keratitis. 

For the plan, maybe include specific treatments like cyclosporine or lifitegrast if the artificial tears aren't enough. Also, mention the need for follow-up. 

I need to structure each section clearly. Let me check if I missed any details from the original report. The patient's occupation is important for the assessment. The duration of symptoms (three months) is also relevant. 

Okay, putting it all together now.

```

## Resposta

**SOAP**  

**Subjetivo (S):**  
Paciente relatou ardência e sensação de areia nos dois olhos há 3 meses, piorando no fim do dia. Trabalha no computador o dia todo. Já utilizou lágrima artificial de tubinho sem melhora significativa.  

**Objetivo (O):**  
- **Exame clínico:** Hiperemia conjuntival leve bilateral.  
- **Testes:**  
  - MEI diminuído com fluoresceína.  
  - Rosa bengal: pontilhado periquerático.  
  - Schirmer: 6 mm OD e 5 mm OE em 5 min.  
  - TBUT: 6 segundos.  
  - Sem ceratite ponteada central.  

**Avaliação (A):**  
Síndrome de olho seco (evaporativo) associada à exposição prolongada à tela de computador. A diminuição da produção lacrimal (Schirmer) e o tempo de tolerância da película lacrimal (TBUT) curto, além das alterações epiteliais detectadas por fluoresceína e rosa bengal, reforçam o diagnóstico.  

**Plano (P):**  
- Continuar uso de lágrimas artificiais (preferencialmente preservante-free).  
- Recomendar compressa quente e higiene das pálpebras.  
- Avaliar uso de lubrificantes oculares de longa duração (ex.: ciclosporina 0,05% ou lifitegrast 5%).  
- Reforçar pausas na atividade de tela (princípio 20-20-20).  
- Aumentar umidade ambiente e hidratação.  
- Encaminhar para oftalmologia para avaliação de ceratite ou outras causas.  
- Reavaliação em 2 semanas.
