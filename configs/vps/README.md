# VPS Stack — LiteLLM Gateway + n8n (lapan-vps)

Public entry for the hospital's local AI, plus workflow automation with
Google Drive. Everything the hospital serves stays tailnet-only
(`tailscale serve`); the VPS is the only public, TLS-terminated hop.

```text
apps / internet → Traefik (api.DOMAIN, n8n.DOMAIN)
                   ├─ LiteLLM :4000  → tailnet → ai-api (lapan-ai:8088)
                   └─ n8n :5678      → LiteLLM + Google Drive (OAuth2)
```

## Prerequisites (VPS)

1. `tailscale up` on the VPS (already true: node `lapan-vps`,
   100.86.170.126) and ACL allowing it to reach `lapan-ai` over 443
   (tailscale serve). Verify from the VPS:
   `curl -s https://lapan-ai.tailf9eac9.ts.net/healthz` (from the tailnet,
   with the hospital's `AI_API_KEY` for `/v1/*`).
2. DNS A records `api.DOMAIN` and `n8n.DOMAIN` → VPS public IP.
3. The existing Traefik must use a docker provider network whose name goes
   in `TRAEFIK_NETWORK` (find it with `docker network ls | grep -i traefik`)
   and an HTTPS entrypoint (`TRAEFIK_ENTRYPOINT`, usually `websecure`).

## Deploy

```bash
mkdir -p /srv/vps && cd /srv/vps
# copy configs/vps/* here (docker-compose.yml, init-dbs.sh,
# litellm-config.yaml, .env) — .env filled from .env.example
docker compose up -d
docker compose logs -f litellm   # wait for "startup complete"
curl -s http://127.0.0.1:4000/health/liveliness
```

## Virtual keys (one per consumer)

```bash
docker exec -it lapan-litellm litellm --config /app/config.yaml \
  --generate_virtual_key --max_budget 50 --duration "30d" --team_id lapan
# or, with the proxy up:
curl -s http://127.0.0.1:4000/key/generate \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"key_alias": "n8n", "models": ["lapan"], "rpm_limit": 30, "max_budget": 50, "budget_duration": "30d"}'
```

Admin UI: `https://api.DOMAIN/ui` (sign in with the master key). Create
keys for: `n8n`, `app-1`, `app-2`. Never hand out the master key.

## Smoke test (end to end)

```bash
curl -s https://api.DOMAIN/v1/chat/completions \
  -H "Authorization: Bearer sk-VIRTUAL-KEY" -H "Content-Type: application/json" \
  -d '{"model": "lapan", "messages": [{"role": "user", "content": "Liste os modelos disponíveis em uma linha."}]}'
```

## n8n + Google Drive

1. Google Cloud Console → new project → enable **Google Drive API** (and
   Google Docs/Sheets if needed) → OAuth consent screen (internal) →
   OAuth client (Web) with redirect `https://n8n.DOMAIN/rest/oauth2-credential/callback`.
2. In n8n: Credentials → Google Drive OAuth2 API → client id/secret →
   Connect (OAuth flow) → save.
3. Workflow "Consulta local a partir do Drive":
   - **Chat Trigger** (ou Webhook / Google Drive Trigger em pasta vigiada)
   - **Google Drive** → Search/Download do arquivo
   - **Extract from File** (PDF/DOCX → texto)
   - **HTTP Request** → `POST https://api.DOMAIN/v1/chat/completions`
     (header `Authorization: Bearer sk-n8n-key`, body com `model: "lapan"`
     e o texto do documento como `user` message)
   - Resposta no chat (e opcionalmente **Google Drive → Upload** do resultado).
4. Point apps at LiteLLM with `base_url=https://api.DOMAIN/v1`.

## LGPD notes

- `turn_off_message_logging: true` — clinical payloads are never stored on
  the VPS; only metadata (model, tokens, key, latency) in Postgres.
- n8n execution data may contain document content: disable "Save execution
  progress" for production workflows touching clinical data, or self-host
  concerns aside, keep executions on the hospital side only.
- Rotate virtual keys periodically (LiteLLM UI); revoke per consumer at
  any time.

## Rollback

`docker compose down` removes the public path instantly; the hospital
keeps working through the SSH tunnel exactly as today. Remove the
`lapan-vps → lapan-ai:443` ACL entry to fully sever the tailnet path.
