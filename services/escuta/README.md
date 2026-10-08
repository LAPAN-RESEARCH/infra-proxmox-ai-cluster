# Escuta Clínica — serviço de escuta ambiente de consultas

Implementação das Fases 1–5 do
[plano de escuta clínica](../../../docs/00-project-context/07-clinical-listening-solution-plan.md):
captação de dois cliques com gravação servidor-side, transcrição ao vivo
(WhisperLiveKit), pipeline batch de fidelidade (ASR determinístico +
diarização + alinhamento palavra×locutor + papéis Médico/Paciente), SOAP por
LLM local com verificação cruzada, revisão em tela dividida e governança
(retenção de 90 dias com expurgo seguro, auditoria, transcript imutável).

## Rodar

No stack (`configs/ai-stack/docker-compose.yml`, serviço `escuta`, porta
`127.0.0.1:8020`):

```bash
cd /srv/ai/compose/core && docker compose up -d --build escuta
```

Desenvolvimento sem GPU (backends stub):

```bash
cd services/escuta
ESCUTA_DATA_DIR=/tmp/escuta ESCUTA_RUN_DIR=/tmp/escuta/run \
ESCUTA_ASR_BACKEND=stub ESCUTA_LLM_BACKEND=stub \
ESCUTA_UNLOAD_TITULAR_ON_JOB=0 \
uvicorn escuta.api:app --port 8020
```

Testes: `PYTHONPATH=. python -m pytest tests/ -q` (31 testes; CPU only).

## Arquitetura em uma tela

```text
navegador (2 cliques) ──WS PCM 16k──► api.py ──► WLK (transcrição ao vivo)
                                        │  gravação servidor-side (.wav→.opus)
                                        ▼
                              fila SQLite ──► worker.py
   decode 16k + passa-alta ─► ASR determinístico ─► pyannote (turnos)
   ─► alinhamento palavra×locutor ─► papéis (ECAPA+heurística+LLM)
   ─► transcript imutável (sha256) ─► SOAP ─► laudo ─► verificação (qwen3:8b)
                                        ▼
                          revisão em tela dividida ─► assinatura
                                        ▼
                     expurgo do áudio após 90 dias (decisão 2026-09-24)
```

## Configuração (variáveis `ESCUTA_*`)

| Variável | Default | Papel |
| --- | --- | --- |
| `ESCUTA_DATA_DIR` | `/srv/ai/clinical` | volume clínico (cifrar com gocryptfs/LUKS) |
| `ESCUTA_RETENTION_DAYS` | `90` | dias pós-assinatura até o expurgo do áudio |
| `ESCUTA_ASR_BACKEND` | `http` | `http` (Speaches) · `embedded` (faster-whisper in-process, perfil determinístico completo) · `stub` |
| `ESCUTA_ASR_URL` / `ESCUTA_ASR_MODEL` | Speaches/turbo | endpoint e modelo ASR |
| `ESCUTA_WLK_URL` | `ws://whisper-livekit:8000/asr` | transcrição ao vivo (falha => só-gravação) |
| `ESCUTA_LLM_URL` / `ESCUTA_SOAP_MODEL` / `ESCUTA_VERIFY_MODEL` | ai-api / `gpt-oss:20b` / `qwen3:8b` | cadeia de 3 chamadas |
| `ESCUTA_OLLAMA_CONTAINER` / `ESCUTA_OLLAMA_MODEL` | `ollama` / `gpt-oss:20b` | preemptação do titular no lock de GPU |
| `ESCUTA_PROMPTS_DIR` | — | sobrepõe os prompts embutidos (`soap.md`, `laudo.md`, `verify.md`, `roles.md`) |
| `ESCUTA_API_TOKEN` | — | auth opcional (header `X-Escuta-Token`; WS `?token=`) |

Chaves existentes são reaproveitadas por nome de variável (`SPEACHES_API_KEY`,
`WLK_API_TOKEN`, `AI_API_KEY`) — configure os `*_ENV` para trocar.

## Endpoints principais

- `POST /api/sessions` → `WS /ws/stream/{id}` (PCM Int16 16k; texto `stop` encerra)
- `POST /api/uploads` (multipart; corpus real/imports)
- `GET /api/jobs/{id}/events` (SSE de progresso)
- `GET/PUT /api/consultations/{id}/soap` · `POST .../sign` · `POST .../roles/swap`
- `POST /api/consultations/{id}/enrollment` (voz do médico)
- `GET /audio/{id}` (404 após expurgo) · `GET /` (UI)
