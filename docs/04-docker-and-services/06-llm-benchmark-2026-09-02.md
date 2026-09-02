# LLM Benchmark — 2026-09-02

Shortlist evaluation for the titular chat model on the RTX 5060 Ti (16 GB),
after the 2026-09 upgrade (Ollama 0.33.2, GPU inference restored, runtime
tuned with `OLLAMA_KEEP_ALIVE=30m`, `OLLAMA_FLASH_ATTENTION=1`,
`OLLAMA_KV_CACHE_TYPE=q8_0`).

- Suite: `scripts/benchmark_llm.py` + 8 synthetic clinical pt-BR cases
  (`configs/ai-stack/benchmark/cases.jsonl`): laudo de retina, extração
  estruturada (JSON), diferencial clínico, nota SOAP, resumo de literatura,
  reescrita formal, conformidade de formato, Q&A farmacológico.
- Raw outputs (blind-review ready): `hugo@lapan-ai:~/benchmark/benchmark-results/20260902-215841/`

## Speed (GPU, 8/8 cases per model)

| Model | avg wall/case | tok/s | VRAM fit | Notes |
|---|---|---|---|---|
| **gpt-oss:20b** | 13.5 s | **89.5** | fits fully (13.8 GB) | MoE 3.6B active, MXFP4 |
| qwen3:8b (ref) | 15.3 s | 74.0 | fits easily | previous default |
| gemma4:26b | 33.6 s | 50.5 | partial CPU offload (19 GB) | MoE 3.8B active |
| qwen3.8:27b | 162.0 s | 8.1 | heavy CPU offload (18 GB dense) | batch-only |

## Objective format/extraction checks

| Model | conformidade-json (single valid JSON) | extracao-exame (8 keys) |
|---|---|---|
| gpt-oss:20b | perfect | complete, direct JSON |
| qwen3.8:27b | perfect | complete, direct JSON |
| gemma4:26b | perfect | complete, JSON inside code fences |
| qwen3:8b | perfect | missing `técnica` field |

## Decision

- **Titular (`model=lapan` no LiteLLM): `gpt-oss:20b`** — fastest, only large
  model that fits the 16 GB card alongside the ASR stack, clean raw JSON.
- `gemma4:26b`: quality alternative / second route (`lapan/gemma4:26b`).
- `qwen3.8:27b` (VLM, 262K ctx): highest apparent quality but 8 tok/s makes
  it unusable interactively on this GPU; reserved for occasional batch runs
  (expect ~3–5 min per long document).
- `qwen3:8b` / `qwen2.5-coder:7b`: kept for tools and coding agents.
- Blind quality review of the 32 outputs by the clinical team is
  recommended before committing to gpt-oss:20b for production laudos;
  switching the titular model is a one-line change in
  `configs/vps/litellm-config.yaml` + `docker compose restart litellm`.

## VRAM budget after the upgrade (16.3 GB total)

| Process | VRAM |
|---|---|
| Ollama gpt-oss:20b | ~12.4–13.8 GB |
| Speaches faster-whisper-large-v3-turbo | ~1.2 GB |
| whisper-livekit (turbo + Sortformer) | ~3–4 GB (loaded on demand) |

gpt-oss:20b + Speaches coexist comfortably; whisper-livekit realtime
sessions should be preferred while the titular model is idle, or accept
model swapping (30 min keep-alive) during long consultations.
