# extracao-exame — Extração estruturada (JSON) de texto de exame

## Prompt

```
Extraia os seguintes campos como JSON com as chaves: paciente, idade, olho, técnica, espessura_macular_central_micras, volume_macular_mm3, achados (lista), conclusao. Texto do exame: 'Tomografia de coerência óptica (OCT) — Spectralis. Paciente: J.M.S., 67 anos. Olho analisado: OD. Varredura macular cubo 20x25. Espessura macular central: 312 micras (limite 270). Volume macular: 11,2 mm³. Observa-se espessamento epirretiniano na região foveal com descontinuidade da linha elipsóide externa e presença de pequena cavidade cística intrarretiniana. Camada de coriocapilar preservada. Conclusão: alterações maculares sugestivas de membrana epirretiniana com edema cístico leve.'
```

## Métricas

- wall: 45.3s | 11.2 tok/s | 481 tokens gerados | thinking: 888 chars | done: stop

## Raciocínio (thinking)

```text
The user wants me to extract structured data from an OCT exam report and return it as valid JSON with specific keys. Let me parse the text:

- paciente: "J.M.S."
- idade: 67
- olho: "OD"
- técnica: "Tomografia de coerência óptica (OCT) — Spectralis" or "Varredura macular cubo 20x25" - I think the technique refers to the method used, which is "Tomografia de coerência óptica (OCT) — Spectralis" and the scan pattern is "Varredura macular cubo 20x25". I'll include the full technique description.
- espessura_macular_central_micras: 312
- volume_macular_mm3: 11.2
- achados (lista): ["espessamento epirretiniano na região foveal", "descontinuidade da linha elipsóide externa", "pequena cavidade cística intrarretiniana", "camada de coriocapilar preservada"]
- conclusao: "alterações maculares sugestivas de membrana epirretiniana com edema cístico leve"

Let me format this as valid JSON.
```

## Resposta

{
  "paciente": "J.M.S.",
  "idade": 67,
  "olho": "OD",
  "técnica": "Tomografia de coerência óptica (OCT) — Spectralis, varredura macular cubo 20x25",
  "espessura_macular_central_micras": 312,
  "volume_macular_mm3": 11.2,
  "achados": [
    "espessamento epirretiniano na região foveal",
    "descontinuidade da linha elipsóide externa",
    "pequena cavidade cística intrarretiniana",
    "camada de coriocapilar preservada"
  ],
  "conclusao": "alterações maculares sugestivas de membrana epirretiniana com edema cístico leve"
}
