# Prompt — Extração estruturada (JSON)

## System

```text
Você extrai dados estruturados de textos de exames/laudos. Responda
APENAS com um objeto JSON válido, sem nenhum texto fora do JSON, sem
markdown. Se um campo não constar no texto, use null. Nunca invente
valores. Números exatamente como no texto (unidade incluída).
```

## User (exemplo — adapte as chaves ao seu caso)

```text
Extraia o objeto JSON com as chaves:
{
  "paciente": string|null,
  "idade": integer|null,
  "olho": "OD"|"OE"|"AO"|null,
  "tecnica": string|null,
  "espessura_macular_central_micras": integer|null,
  "volume_macular_mm3": number|null,
  "achados": [string],
  "conclusao": string|null
}

TEXTO:
{{texto_do_exame}}
```

## Parsing no seu código

```python
import json, re
raw = resp.choices[0].message.content.strip()
# Alguns modelos cercam o JSON com code fences — remova se presente:
m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", raw, re.S)
if m:
    raw = m.group(1)
data = json.loads(raw)
```

No benchmark de 2026-09, o `gpt-oss:20b` devolveu JSON puro direto em
100% dos casos (docs/results/20260902-215841) — o fallback de fences é
só seguro-guarda.
