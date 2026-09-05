# Tutorial 10 — Troubleshooting

Sintoma → causa provável → comando de confirmação → correção.

## Hospital (lapan-ai)

### "O chat/modelo ficou lento de repente"

Causa nº 1: **inferência caiu para CPU** (já aconteceu — silencioso).

```bash
ssh hugo@lapan-ai 'curl -s http://127.0.0.1:11434/api/ps'   # size_vram > 0?
nvidia-smi --query-compute-apps=pid,used_memory --format=csv,noheader
```

`size_vram: 0` = CPU. Correção: `cd /srv/ai/compose/core && sudo docker
compose up -d --force-recreate ollama` (re-anexa a GPU). Depois confira
tok/s (~70–90 no 20b; <10 = CPU/offload).

### "Modelo não encontrado / 412 no pull"

Ollama velho para modelos novos: `sudo docker compose pull ollama && sudo
docker compose up -d --force-recreate ollama`.

### "Transcrição realtime não conecta (porta 8010)"

- Túnel com `-L 8010:127.0.0.1:8010` ativo?
- Token correto (`WLK_API_TOKEN` no `.env`)?
- Container: `sudo docker logs whisper-livekit --tail 20`.

### "GPU sem memória / consulta lenta com modelo carregado"

Orçamento da 5060 Ti: gpt-oss:20b (~13 GB) + Speaches (1,2 GB) + WLK
(~3 GB). Em sessões de transcrição longas, deixe o chat idle (o Ollama
descarrega após `OLLAMA_KEEP_ALIVE=30m`) ou aceite offload.

## VPS

### 401 na API pública

Chave inválida/bloqueada. Confira o inventário (tutorial 02) e o header
`Authorization: Bearer sk-...` (sem prefixo extra).

### 429

Rate-limit do Traefik (30 rpm) OU limite da chave virtual. Para o app
principal, suba o middleware no compose (`lapan-api-ratelimit.average`)
ou o `rpm_limit` da chave.

### Certificado/TLS "inválido" para api/n8n.lapan.cloud

Let's Encrypt rate-limited (tentativas antes do DNS existir). O Traefik
re-tenta com backoff; se demorar: `docker restart traefik` força nova
tentativa. Ver log: `docker logs traefik --since 10m | grep acme`.

### LiteLLM 500 "InternalServerError" em chat

Normalmente o upstream ainda carregando o modelo (frio) ou timeout.
Repetir; se persistir, teste o hospital direto do VPS:
`curl https://lapan-ai.tailf9eac9.ts.net/healthz` (deve pedir bearer).

### n8n: webhook de produção 404

Workflow não **publicado** (draft/publish do n8n 2.3x): abra o workflow →
Publish/Active. Ativar via banco não registra webhook.

### n8n: "Unable to sign without access token" (nó Google)

Credencial Google sem Connect: Credentials → Google Drive (LAPAN) →
Connect (consent). Erro `redirect_uri_mismatch` = redirect errado no
Google Cloud (o certo: `https://n8n.lapan.cloud/rest/oauth2-credential/callback`).

## Geral

- **Restaurar algo**: tutorial 11 (backup de segredos).
- **Estado geral**: snapshots no backup (`snapshots/`) têm portas,
  modelos, chaves e containers esperados de cada servidor.
