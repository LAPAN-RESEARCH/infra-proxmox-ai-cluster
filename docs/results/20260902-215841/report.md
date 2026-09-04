# Benchmark LLM — 20260902-215841

VRAM de pico global: **15509 MiB** (soma de todos os processos GPU, inclui modelos residuais)

| Modelo | Caso | wall(s) | tok/s | tokens | done |
|---|---|---|---|---|---|
| qwen3:8b | laudo-retina | 30.17 | 71.8 | 1550 | stop |
| qwen3:8b | extracao-exame | 10.6 | 74.0 | 768 | stop |
| qwen3:8b | diferencial-clinico | 28.55 | 72.1 | 2048 | length |
| qwen3:8b | nota-soap | 12.25 | 74.0 | 892 | stop |
| qwen3:8b | resumo-artigo | 13.6 | 73.5 | 984 | stop |
| qwen3:8b | reescrita-formal | 5.54 | 75.9 | 409 | stop |
| qwen3:8b | conformidade-json | 5.48 | 76.0 | 409 | stop |
| qwen3:8b | qa-medicamento | 15.87 | 74.4 | 1175 | stop |
| gpt-oss:20b | laudo-retina | 25.99 | 89.3 | 1393 | stop |
| gpt-oss:20b | extracao-exame | 4.01 | 92.0 | 356 | stop |
| gpt-oss:20b | diferencial-clinico | 23.07 | 89.2 | 2048 | length |
| gpt-oss:20b | nota-soap | 9.64 | 89.1 | 848 | stop |
| gpt-oss:20b | resumo-artigo | 13.58 | 88.3 | 1184 | stop |
| gpt-oss:20b | reescrita-formal | 4.12 | 88.1 | 353 | stop |
| gpt-oss:20b | conformidade-json | 5.35 | 91.5 | 480 | stop |
| gpt-oss:20b | qa-medicamento | 22.52 | 88.4 | 1981 | stop |
| gemma4:26b | laudo-retina | 69.8 | 40.3 | 1482 | stop |
| gemma4:26b | extracao-exame | 24.11 | 59.8 | 1376 | stop |
| gemma4:26b | diferencial-clinico | 47.51 | 44.1 | 2048 | length |
| gemma4:26b | nota-soap | 25.98 | 50.3 | 1257 | stop |
| gemma4:26b | resumo-artigo | 26.43 | 55.1 | 1392 | stop |
| gemma4:26b | reescrita-formal | 26.5 | 52.4 | 1338 | stop |
| gemma4:26b | conformidade-json | 14.91 | 51.4 | 715 | stop |
| gemma4:26b | qa-medicamento | 33.52 | 50.2 | 1636 | stop |
| qwen3.8:27b | laudo-retina | 298.67 | 7.4 | 2048 | length |
| qwen3.8:27b | extracao-exame | 45.3 | 11.2 | 481 | stop |
| qwen3.8:27b | diferencial-clinico | 286.5 | 7.2 | 2048 | length |
| qwen3.8:27b | nota-soap | 126.17 | 7.5 | 923 | stop |
| qwen3.8:27b | resumo-artigo | 167.29 | 7.7 | 1268 | stop |
| qwen3.8:27b | reescrita-formal | 42.28 | 8.1 | 325 | stop |
| qwen3.8:27b | conformidade-json | 69.01 | 7.8 | 523 | stop |
| qwen3.8:27b | qa-medicamento | 261.15 | 7.9 | 2048 | length |

## Médias por modelo

- **qwen3:8b**: média 15.3s/caso, 74.0 tok/s (8/8 ok)
- **gpt-oss:20b**: média 13.5s/caso, 89.5 tok/s (8/8 ok)
- **gemma4:26b**: média 33.6s/caso, 50.5 tok/s (8/8 ok)
- **qwen3.8:27b**: média 162.0s/caso, 8.1 tok/s (8/8 ok)

## Como pontuar qualidade

Compare às cegas os arquivos em `outputs/<model>/<case>.md` (critérios por caso no
`cases.jsonl`, campo `rubric`). Nota 0-5 por caso; some por modelo.

