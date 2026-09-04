# qa-medicamento — Q&A de dosagem/segurança

## Prompt

```
Paciente com glaucoma primário de ângulo aberto usa maleato de timolol 0,5% duas vezes ao dia e apresentou bradicardia sintomática. Quais as alternativas tópicas de primeira linha, com princípio ativo, concentração usual e posologia, e qual classe é preferida neste cenário cardiovascular? Inclua ao final uma linha 'ALERTA' com o que deve ser verificado antes de qualquer troca.
```

## Métricas

- wall: 33.52s | 50.2 tok/s | 1636 tokens gerados | thinking: 3729 chars | done: stop

## Raciocínio (thinking)

```text

*   Patient: Primary Open-Angle Glaucoma (POAG).
*   Current Medication: Timolol maleate 0.5% eye drops, BID (twice a day).
*   Adverse Event: Symptomatic bradycardia.
*   Goal: Identify first-line topical alternatives, including active ingredient, usual concentration, and dosage.
*   Specific Question: Which class is preferred in this cardiovascular scenario?
*   Constraint: Must include an "ALERTA" line at the end regarding what to check before switching.
*   Persona: Pharmacological assistant (must signal uncertainty and the need for professional consultation).

    *   Timolol is a non-selective beta-blocker.
    *   Systemic absorption (via nasolacrimal duct) can cause bradycardia, heart block, and bronchospasm.
    *   Symptomatic bradycardia is a contraindication/reason to discontinue beta-blockers.

    *   *Prostaglandin Analogs (PGAs):* Latanoprost, Travoprost, Bimatoprost. These are generally considered first-line for POAG due to efficacy and minimal systemic cardiovascular impact.
    *   *Alpha-2 Adrenergic Agonists:* Brimonidine. (Note: Can cause CNS effects/sedation, but less impact on heart rate than beta-blockers, though still used).
    *   *Rho Kinase Inhibitors:* Netarsudil (newer, less common in all regions).
    *   *Carbonic Anhydrase Inhibitors (CAIs):* Dorzolamide, Brinzolamide. (Usually second-line or adjunct).

    *   *Preferred Class:* Prostaglandin Analogs (PGAs). They are the gold standard for first-line therapy in POAG and do not affect heart rate/conduction like beta-blockers.

    *   *Latanoprost:* 0.005%, 1x/day.
    *   *Travoprost:* 0.004%, 1x/day.
    *   *Bimatoprost:* 0.01%, 1x/day.

    *   *Disclaimer:* I am an AI assistant. This is information, not medical advice. Consult an ophthalmologist and cardiologist.
    *   *Analysis:* Explain *why* Timolol caused this (systemic absorption).
    *   *Preferred Class:* Prostaglandin Analogs (Análogos de Prostaglandinas).
    *   *Alternatives Table/List:*
        1.  Latanoprost (0,005%, 1x/dia).
        2.  Travoprost (0,004%, 1x/dia).
        3.  Bimatoprost (0,01%, 1x/dia).
    *   *Alternative (if PGA isn't enough/suitable):* Brimonidine (0,1% ou 0,2%, 3x/dia) - though PGAs are the primary answer.
    *   *ALERTA:* Check intraocular pressure (IOP) stability and potential side effects (pigmentation, lash growth, etc.) and ensure the patient's cardiovascular status is managed.

    *   *Wait, the prompt asks for "alternativas tópicas de primeira linha".* In modern guidelines (AAO, etc.), PGAs are the first-line choice.
    *   *Concentrations:*
        *   Latanoprost: 0.005%
        *   Travoprost: 0.004%
        *   Bimatoprost: 0.01%
    *   *Dosage:* Once daily (usually at night).

    *   Pharmacological assistant persona? Yes.
    *   Signal uncertainty/professional check? Yes.
    *   Alternatives included? Yes.
    *   Active ingredient, concentration, dosage included? Yes.
    *   Preferred class identified? Yes.
    *   'ALERTA' line included? Yes.

    *   *Intro:* Disclaimer.
    *   *Explanation:* Timolol (non-selective beta-blocker) can cause systemic effects via nasolacrimal absorption.
    *   *Preferred Class:* Análogos de Prostaglandinas (PGAs).
    *   *List:*
        *   Latanoprost (0,005%, 1x/dia).
        *   Travoprost (0,004%, 1x/dia).
        *   Bimatoprost (0,01%, 1x/dia).
    *   *Secondary option (Alpha-2):* Brimonidina (0,1% ou 0,2%, 3x/dia).
    *   *ALERTA:* Monitoramento da PIO e avaliação da estabilidade hemodinâmica pelo médico.

    *(Self-Correction during drafting)*: Make sure to emphasize that PGAs are preferred because they act primarily on uveoscleral outflow and have minimal systemic cardiovascular impact compared to beta-blockers.
```

## Resposta

***Atenção: Eu sou um assistente de inteligência artificial e forneço informações baseadas em literatura farmacológica. Esta resposta não substitui a consulta médica ou a prescrição de um profissional de saúde. A bradicardia sintomática é uma condição clínica que exige avaliação médica imediata (Oftalmologista e Cardiologista).***

O maleato de timolol é um betabloqueador não seletivo. Embora seja aplicado topicamente, parte da droga é absorvida sistemicamente através do ducto nasolacrimal, podendo causar efeitos adversos cardiovasculares, como bradicardia e bloqueios de condução, especialmente em pacientes sensíveis.

### Classe Preferida neste Cenário
Neste cenário cardiovascular, a classe de primeira linha preferida é a dos **Análogos de Prostaglandinas (PGAs)**. Eles são preferidos porque atuam aumentando o escoamento uveoescleral do humor aquoso e apresentam um perfil de segurança cardiovascular significativamente superior aos betabloqueadores, com mínima absorção sistêmica que impacte a frequência cardíaca.

### Alternativas Tópicas de Primeira Linha

| Princípio Ativo | Concentração Usual | Posologia Comum |
| :--- | :--- | :--- |
| **Latanoprost** | 0,005% | 1 gota no olho afetado, 1 vez ao dia (geralmente à noite). |
| **Travoprost** | 0,004% | 1 gota no olho afetado, 1 vez ao dia (geralmente à noite). |
| **Bimatoprost** | 0,01% | 1 gota no olho afetado, 1 vez ao dia (geralmente à noite). |

*Nota: Em alguns casos, se a monoterapia com prostaglandina não for suficiente, pode-se considerar o uso de agonistas alfa-2 adrenérgicos (como a **Brimonidina 0,1% ou 0,2%, 3x ao dia**), que também possuem impacto cardiovascular menor que os betabloqueadores, embora exijam cautela em pacientes com depressão do sistema nervoso central.*

**ALERTA: Antes de qualquer troca, deve-se verificar a estabilidade da Pressão Intraocular (PIO) do paciente e realizar uma avaliação clínica rigorosa da função cardíaca e do ritmo sinusal para garantir que a suspensão do timolol e a introdução da nova classe sejam seguras.**
