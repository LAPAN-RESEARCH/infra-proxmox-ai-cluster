# extracao-exame — Extração estruturada (JSON) de texto de exame

## Prompt

```
Extraia os seguintes campos como JSON com as chaves: paciente, idade, olho, técnica, espessura_macular_central_micras, volume_macular_mm3, achados (lista), conclusao. Texto do exame: 'Tomografia de coerência óptica (OCT) — Spectralis. Paciente: J.M.S., 67 anos. Olho analisado: OD. Varredura macular cubo 20x25. Espessura macular central: 312 micras (limite 270). Volume macular: 11,2 mm³. Observa-se espessamento epirretiniano na região foveal com descontinuidade da linha elipsóide externa e presença de pequena cavidade cística intrarretiniana. Camada de coriocapilar preservada. Conclusão: alterações maculares sugestivas de membrana epirretiniana com edema cístico leve.'
```

## Métricas

- wall: 4.01s | 92.0 tok/s | 356 tokens gerados | thinking: 753 chars | done: stop

## Raciocínio (thinking)

```text
We need to produce JSON with keys: paciente, idade, olho, técnica, espessura_macular_central_micras, volume_macular_mm3, achados (lista), conclusao.

We have patient: J.M.S., 67 anos. So paciente: "J.M.S." idade: 67. olho: "OD". técnica: "Spectralis". espessura_macular_central_micras: 312 micras. volume_macular_mm3: 11,2 mm³. Achados: list of findings: "espessamento epirretiniano na região foveal", "descontinuidade da linha elipsóide externa", "presença de pequena cavidade cística intrarretiniana", "camada de coriocapilar preservada". Conclusão: "alterações maculares sugestivas de membrana epirretiniana com edema cístico leve." Ensure JSON valid. Use numeric for volume maybe 11.2. Use integer for espessura. Provide keys exactly. Let's produce.
```

## Resposta

{"paciente":"J.M.S.","idade":67,"olho":"OD","técnica":"Spectralis","espessura_macular_central_micras":312,"volume_macular_mm3":11.2,"achados":["espessamento epirretiniano na região foveal","descontinuidade da linha elipsóide externa","presença de pequena cavidade cística intrarretiniana","camada de coriocapilar preservada"],"conclusao":"alterações maculares sugestivas de membrana epirretiniana com edema cístico leve."}
