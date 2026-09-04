# reescrita-formal — Reescrita formal de texto coloquial

## Prompt

```
Reescreva formalmente: 'aí o paciente voltou falando que o olho tava doendo bastante de novo, a gente viu que a pressão subiu pra 32 no olho direito, acho que foi aquela reação do remédio mesmo, a gota que ele tava usando. Mandei parar a gota, passei outra pra baixar a pressão e pedi pra voltar semana que vem. Se não melhorar, vamos ter que pensar em cirurgia.'
```

## Métricas

- wall: 26.5s | 52.4 tok/s | 1338 tokens gerados | thinking: 3035 chars | done: stop

## Raciocínio (thinking)

```text

*   *Original:* "aí o paciente voltou falando que o olho tava doendo bastante de novo, a gente viu que a pressão subiu pra 32 no olho direito, acho que foi aquela reação do remédio mesmo, a gota que ele tava usando. Mandei parar a gota, passei outra pra baixar a pressão e pedi pra voltar semana que vem. Se não melhorar, vamos ter que pensar em cirurgia."
    *   *Key Information:*
        1.  Patient returned with complaints of significant ocular pain (recurrent).
        2.  Intraocular pressure (IOP) measured 32 mmHg in the right eye (OD).
        3.  Suspected cause: Adverse reaction to the previous topical medication (eye drops).
        4.  Action taken: Discontinued previous medication; prescribed new medication to reduce IOP.
        5.  Follow-up: Scheduled for next week.
        6.  Contingency plan: Surgical intervention if clinical improvement is not achieved.

    *   *Register:* Technical-formal (medical/clinical documentation).
    *   *Constraint:* Do not change meaning.

    *   "o paciente voltou falando que o olho tava doendo bastante de novo" $\rightarrow$ O paciente retornou apresentando queixa de dor ocular intensa e recorrente.
    *   "a gente viu que a pressão subiu pra 32 no olho direito" $\rightarrow$ Ao exame, constatou-se elevação da pressão intraocular (PIO) para 32 mmHg no olho direito (OD).
    *   "acho que foi aquela reação do remédio mesmo, a gota que ele tava usando" $\rightarrow$ Suspeita-se de reação adversa ao colírio previamente prescrito.
    *   "Mandei parar a gota, passei outra pra baixar a pressão" $\rightarrow$ Foi determinada a suspensão do fármaco anterior e prescrita nova terapia hipotensora ocular.
    *   "pedi pra voltar semana que vem" $\rightarrow$ Solicitado retorno para acompanhamento em uma semana.
    *   "Se não melhorar, vamos ter que pensar em cirurgia" $\rightarrow$ Caso não haja resposta clínica satisfatória, será avaliada a necessidade de intervenção cirúrgica.

    *   *Option 1: Clinical Evolution/Medical Record style (most common for doctors).*
        "Paciente retorna com queixa de dor ocular intensa e recorrente. Ao exame, observou-se elevação da pressão intraocular (PIO) para 32 mmHg no olho direito (OD), possivelmente decorrente de reação adversa ao colírio em uso anterior. Foi determinada a suspensão da medicação prévia e prescrita nova terapia para redução da PIO. O paciente foi orientado a retornar em uma semana para reavaliação; caso não haja melhora clínica, será considerada a intervenção cirúrgica."

    *   *Option 2: More concise/Direct (Standard medical note).*
        "Paciente apresenta recidiva de dor ocular intensa. Constatada PIO de 32 mmHg em OD, com suspeita de reação adversa ao colírio utilizado anteriormente. Conduta: suspensão do fármaco anterior e prescrição de novo agente hipotensor. Retorno agendado para uma semana. Em caso de persistência do quadro, será avaliada conduta cirúrgica."

    *   Does it change meaning? No.
    *   Is it technical-formal? Yes.
    *   Is it professional? Yes.
```

## Resposta

Aqui estão três opções de reescrita, dependendo do contexto (prontuário médico, relatório ou comunicação entre colegas):

**Opção 1: Registro em Prontuário (Estilo Evolução Clínica)**
*Ideal para documentação oficial de atendimento.*

> "Paciente retorna com queixa de dor ocular intensa e recorrente. Ao exame, constatou-se elevação da pressão intraocular (PIO) para 32 mmHg no olho direito (OD), com suspeita de reação adversa ao colírio utilizado anteriormente. Foi determinada a suspensão da medicação prévia e prescrita nova terapia hipotensora ocular. Solicitado retorno para reavaliação em uma semana. Caso não haja resposta clínica satisfatória, será avaliada a necessidade de intervenção cirúrgica."

**Opção 2: Relatório Técnico (Estilo mais descritivo)**
*Ideal para encaminhamentos ou laudos.*

> "O paciente apresentou recidiva de quadro álgico ocular. Durante a avaliação, verificou-se um aumento da pressão intraocular no olho direito, atingindo 32 mmHg, possivelmente decorrente de efeito adverso ao fármaco tópico em uso. A conduta consistiu na interrupção do uso do colírio anterior e na introdução de uma nova medicação para controle da pressão. O paciente foi orientado a retornar em sete dias para acompanhamento; a persistência do quadro poderá indicar a necessidade de procedimento cirúrgico."

**Opção 3: Comunicação Profissional (Direta e Concisa)**
*Ideal para mensagens ou e-mails entre profissionais de saúde.*

> "Paciente apresenta retorno com queixa de dor ocular importante. Constatada PIO de 32 mmHg em OD, com suspeita de reação ao colírio prescrito anteriormente. Conduta: suspensão da medicação anterior e prescrição de novo agente hipotensor. Retorno agendado para uma semana. Em caso de ausência de melhora, será considerada a conduta cirúrgica."

**Principais alterações terminológicas realizadas:**
*   *“Olho doendo bastante”* $\rightarrow$ **Dor ocular intensa / Quadro álgico.**
*   *“Pressão subiu pra 32”* $\rightarrow$ **Elevação da pressão intraocular (PIO) para 32 mmHg.**
*   *“Reação do remédio/gota”* $\rightarrow$ **Reação adversa / Efeito adverso ao fármaco tópico.**
*   *“Mandei parar/passei outra”* $\rightarrow$ **Suspensão da medicação / Prescrição de nova terapia.**
*   *“Pensar em cirurgia”* $\rightarrow$ **Avaliar necessidade de intervenção cirúrgica.**
