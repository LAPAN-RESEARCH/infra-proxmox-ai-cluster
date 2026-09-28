# Performance da Escuta Clínica — 2026-09-26

Medições reais na VM `lapan-ai` (RTX 5060 Ti 16 GB), corpus sintético
neuropediátrico de 21,47 min (Edge Neural TTS, 2 vozes, ruído HVAC calibrado;
ground truth TXT/RTTM do agent-neurovision-assistant).

## ASR (faster-whisper large-v3-turbo via Speaches, GPU)

| Variante | RTF | WER normalizado | CER |
| --- | --- | --- | --- |
| clean | 0,055–0,067 | **5,4%** | 6,9% |
| 15 dB SNR (ar-condicionado típico) | 0,056–0,097 | **3,1%** | 3,9% |

- Gates da Fase 0 (WER < 12%, RTF ≤ 0,15): **aprovados com folga**.
- 60 min de consulta ≈ **4 min** de ASR. Ruído HVAC não degrada (VAD + passa-alta robustos).

## Diarização (pyannote community-1)

| Métrica | CPU (antes) | **CUDA (agora)** |
| --- | --- | --- |
| RTF (21,5 min) | > 0,45 (não terminava em 10 min) | **0,044 (57 s)** |
| VRAM | 0 | ~0,5–1 GB |
| **DER vs RTTM** | — | **25,4%** (gate < 15%: reprovado) |

DER dominado por *missed detection* (132 s) e *confusão* (180 s): vozes TTS no
mesmo canal são o caso difícil conhecido; melhorias previstas: re-clustering
por embeddings do pipeline, migração a speaker-diarization-3.1 (termos dos
sub-modelos) e validação com gravação real de duas pessoas. A tripla checagem
de papéis + revisão humana cobrem o risco operacional enquanto isso.

## Cadeia LLM (qwen3:8b único, residente 6,4 GB)

SOAP 4 s · laudo 4 s · verificação 2 s (74 tok/s, think off; num_ctx 8192).

## Pipeline completo (upload → SOAP pronta)

- 60 s de áudio: **16–23 s** total.
- 60 min de consulta (extrapolação): **≈ 5–6 min** (ASR 4 + diarização 2,7 + LLM ~1 com map-reduce).

## Orçamento de VRAM (coexistência confirmada)

qwen3:8b 6,4 + Speaches turbo 1,2 + diarização ~1 + folga ≈ **8,6 GB de 16,3**
(suficiente até para sessão realtime WLK simultânea, ~4 GB).

## Decisões de performance tomadas

1. qwen3:8b modelo único (latência primeira; sem swaps de contexto).
2. Diarização CUDA obrigatória p/ consultas longas (CPU estouraria 40+ min).
3. torch+torchaudio exclusivamente do PyPI (mistura de índices cu12/cu13 quebra o torchaudio).
4. `ESCUTA_LAUDO_MODEL` para titular maior em batch noturno sem tocar o fluxo do consultório.
