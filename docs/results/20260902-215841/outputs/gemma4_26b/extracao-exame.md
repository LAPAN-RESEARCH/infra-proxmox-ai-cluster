# extracao-exame — Extração estruturada (JSON) de texto de exame

## Prompt

```
Extraia os seguintes campos como JSON com as chaves: paciente, idade, olho, técnica, espessura_macular_central_micras, volume_macular_mm3, achados (lista), conclusao. Texto do exame: 'Tomografia de coerência óptica (OCT) — Spectralis. Paciente: J.M.S., 67 anos. Olho analisado: OD. Varredura macular cubo 20x25. Espessura macular central: 312 micras (limite 270). Volume macular: 11,2 mm³. Observa-se espessamento epirretiniano na região foveal com descontinuidade da linha elipsóide externa e presença de pequena cavidade cística intrarretiniana. Camada de coriocapilar preservada. Conclusão: alterações maculares sugestivas de membrana epirretiniana com edema cístico leve.'
```

## Métricas

- wall: 24.11s | 59.8 tok/s | 1376 tokens gerados | thinking: 3494 chars | done: stop

## Raciocínio (thinking)

```text
*   Task: Extract structured data from an exam text.
    *   Output Format: Valid JSON ONLY (no extra text).
    *   Keys required: `paciente`, `idade`, `olho`, `técnica`, `espessura_macular_central_micras`, `volume_macular_mm3`, `achados` (list), `conclusao`.
    *   Input Text: "Tomografia de coerência óptica (OCT) — Spectralis. Paciente: J.M.S., 67 anos. Olho analisado: OD. Varredura macular cubo 20x25. Espessura macular central: 312 micras (limite 270). Volume macular: 11,2 mm³. Observa-se espessamento epirretiniano na região foveal com descontinuidade da linha elipsóide externa e presença de pequena cavidade cística intrarretiniana. Camada de coriocapilar preservada. Conclusão: alterações maculares sugestivas de membrana epirretiniana com edema cístico leve."

    *   `paciente`: "J.M.S."
    *   `idade`: 67 (or "67 anos") -> Usually, numbers are better for JSON, but I'll stick to the value provided. Let's use 67.
    *   `olho`: "OD"
    *   `técnica`: "Varredura macular cubo 20x25" (or "Tomografia de coerência óptica (OCT) — Spectralis. Varredura macular cubo 20x25") -> Let's include the scan type.
    *   `espessura_macular_central_micras`: 312
    *   `volume_macular_mm3`: 11.2 (Note: input uses comma "11,2", JSON needs dot "11.2" for float, or string "11,2". I'll use a number if possible or string to be safe. Let's use 11.2).
    *   `achados`:
        1. "espessamento epirretiniano na região foveal"
        2. "descontinuidade da linha elipsóide externa"
        3. "presença de pequena cavidade cística intrarretiniana"
        4. "Camada de coriocapilar preservada"
    *   `conclusao`: "alterações maculares sugestivas de membrana epirretiniana com edema cístico leve"

    ```json
    {
      "paciente": "J.M.S.",
      "idade": 67,
      "olho": "OD",
      "técnica": "Varredura macular cubo 20x25",
      "espessura_macular_central_micras": 312,
      "volume_macular_mm3": 11.2,
      "achados": [
        "espessamento epirretiniano na região foveal",
        "descontinuidade da linha elipsóide externa",
        "presença de pequena cavidade cística intrarretiniana",
        "Camada de coriocapilar preservada"
      ],
      "conclusao": "alterações maculares sugestivas de membrana epirretiniana com edema cístico leve"
    }
    ```

    *   `paciente`: J.M.S. (Check)
    *   `idade`: 67 (Check)
    *   `olho`: OD (Check)
    *   `técnica`: Varredura macular cubo 20x25 (Check)
    *   `espessura_macular_central_micras`: 312 (Check)
    *   `volume_macular_mm3`: 11.2 (Check)
    *   `achados`: List of findings (Check)
    *   `conclusao`: Conclusion string (Check)

    *Self-correction on `volume_macular_mm3`*: The input says "11,2". In JSON, numbers use `.`. I will convert it to a float.

    *Self-correction on `técnica`*: The text says "Tomografia de coerência óptica (OCT) — Spectralis. ... Varredura macular cubo 20x25". I'll include the scan method.

    *Refined list of achados*:
    - "espessamento epirretiniano na região foveal"
    - "descontinuidade da linha elipsóide externa"
    - "presença de pequena cavidade cística intrarretiniana"
    - "Camada de coriocapilar preservada"

    *Final JSON structure check*:
    `{"paciente": "...", "idade": ..., "olho": "...", "técnica": "...", "espessura_macular_central_micras": ..., "volume_macular_mm3": ..., "achados": [...], "conclusao": "..."}`

    Wait, the prompt asks for `espessura_macular_central_micras` and `volume_macular_mm3`.

    Let's produce the final JSON.
```

## Resposta

```json
{
  "paciente": "J.M.S.",
  "idade": 67,
  "olho": "OD",
  "técnica": "Varredura macular cubo 20x25",
  "espessura_macular_central_micras": 312,
  "volume_macular_mm3": 11.2,
  "achados": [
    "espessamento epirretiniano na região foveal",
    "descontinuidade da linha elipsóide externa",
    "presença de pequena cavidade cística intrarretiniana",
    "Camada de coriocapilar preservada"
  ],
  "conclusao": "alterações maculares sugestivas de membrana epirretiniana com edema cístico leve"
}
```
