# Tutorial 11 — Restauração a partir do backup de segredos

O backup é gerado por `scripts/backup_secrets.sh` em
`~/Documents/LAPAN/backups/secrets-AAAAMMDD-HHMM/` (permissões 700/600,
fora do repositório). Este guia mapeia cada artefato para o destino de
produção e define a ordem de recuperação.

## Antes de começar

- Verifique se os dois hosts estão acessíveis: `ssh hugo@lapan-ai` e
  `ssh root@lapan-vps`.
- O repositório é a fonte dos arquivos **não-secretos** (compose, configs,
  serviços). O backup cobre o que **não** pode vir do git: segredos, dumps
  e estado.
- Substitua `$B` pelo caminho do backup, ex.:
  `B=~/Documents/LAPAN/backups/secrets-20260904-0821`.

## Ordem de recuperação (doserviço mais básico ao mais alto)

### 1. Hospital (lapan-ai) — stack base

```bash
# Segredos do compose (só depois de existir /srv/ai/compose/core/)
scp $B/lapan-ai/compose-core/.env hugo@lapan-ai:/srv/ai/compose/core/.env
ssh hugo@lapan-ai 'chmod 600 /srv/ai/compose/core/.env'

# Divergentes não-commitáveis (se não forem resolver via repo)
scp $B/lapan-ai/research-platform.yaml hugo@lapan-ai:/srv/ai/rag/configs/

# Subir a stack (sudo): pelo repo sincronizado ou pelo compose do backup
ssh hugo@lapan-ai 'cd /srv/ai/compose/core && sudo docker compose up -d'
```

Modelos Ollama são re-pulláveis — a lista exata está em
`$B/snapshots/lapan-ai-state.txt` (`ollama list`): `gpt-oss:20b`,
`gemma4:26b`, `qwen3.8:27b`, `qwen3:8b`, `qwen2.5-coder:7b`, `bge-m3`,
`embeddinggemma`. Os modelos HuggingFace (turbo, reranker, Sortformer)
re-baixam sozinhos no primeiro uso.

### 2. Exposição tailnet (hospital)

```bash
ssh hugo@lapan-ai 'sudo tailscale serve --bg 8088'
```

### 3. VPS — segredos e stack

```bash
scp $B/lapan-vps/.env root@lapan-vps:/srv/vps/.env
ssh root@lapan-vps 'chmod 600 /srv/vps/.env; chown root:root /srv/vps/.env'
scp $B/lapan-vps/searxng-settings.yml root@lapan-vps:/srv/vps/
scp $B/lapan-vps/acme.json \
  root@lapan-vps:/var/lib/docker/volumes/survey_traefik_letsencrypt/_data/acme.json
ssh root@lapan-vps 'chmod 600 /var/lib/docker/volumes/survey_traefik_letsencrypt/_data/acme.json'

# Stack completa (compose e litellm-config vêm do repo — use-o)
cd configs/vps && scp docker-compose.yml litellm-config.yaml init-dbs.sh \
  searxng-settings.yml root@lapan-vps:/srv/vps/
ssh root@lapan-vps 'cd /srv/vps && chown 1000:1000 init-dbs.sh && docker compose up -d'
```

### 4. VPS — bancos (LiteLLM e n8n)

Só se os bancos estiverem vazios/perdidos (o `init-dbs.sh` cria o `n8n`):

```bash
cat $B/lapan-vps/pg_litellm.sql | ssh root@lapan-vps \
  'docker exec -i lapan-postgres psql -U lapan litellm'
cat $B/lapan-vps/pg_n8n.sql | ssh root@lapan-vps \
  'docker exec -i lapan-postgres psql -U lapan n8n'
```

Isso restaura chaves virtuais (com spend), credenciais n8n **cifradas pela
`N8N_ENCRYPTION_KEY` do `.env` restaurado no passo 3** (a chave e o dump
precisam ser do MESMO backup) e o workflow.

### 5. VPS — workflow e credencial (alternativa cirúrgica aos dumps)

Se os bancos estão íntegros e só o workflow/credencial sumiram:

```bash
scp $B/lapan-vps/n8n-files/n8n-wf.json $B/lapan-vps/n8n-files/n8n-cred.json \
  root@lapan-vps:/srv/vps/n8n/files/
ssh root@lapan-vps 'chown 1000:1000 /srv/vps/n8n/files/n8n-{wf,cred}.json && \
  docker exec lapan-n8n n8n import:workflow --input=/files/n8n-wf.json && \
  docker exec lapan-n8n n8n import:credentials --input=/files/n8n-cred.json'
# Depois: abrir no n8n e PUBLICAR o workflow (modelo draft/published).
```

### 6. Open WebUI (hospital) — se o backup manual foi feito

```bash
scp open-webui-AAAAMMDD.tgz hugo@lapan-ai:/tmp/
ssh hugo@lapan-ai 'sudo tar xzf /tmp/open-webui-*.tgz -C /srv/ai/open-webui && \
  sudo docker restart open-webui'
```

### 7. Verificação final (checklist)

```bash
ssh hugo@lapan-ai 'curl -s http://127.0.0.1:11434/api/ps'        # modelo em VRAM
curl -s https://api.lapan.cloud/health/liveliness                 # "I'm alive!"
# chat de teste com uma chave virtual do dump (ex.: n8n-workflow)
curl -s https://n8n.lapan.cloud/webhook/health                    # n8n responde
```

## Notas importantes

- **Pares inseparáveis**: `pg_n8n.sql` + `N8N_ENCRYPTION_KEY` (mesmo backup);
  `acme.json` + roteadores Traefik (senão o Let's Encrypt re-emite por HTTP-01,
  sujeito a rate limit).
- A `AI_API_KEY` (hospital) e a `LAPAN_AI_API_KEY` (VPS) precisam ser IGUAIS —
  ambas vêm do mesmo backup por construção.
- Chaves virtuais bloqueadas de teste (`lapan-test*`, `app-smoke`,
  `smoke-final`) voltam bloqueadas no dump — correto.
- Multi-factor de tempo: `multicli/` é um serviço pessoal do usuário no
  hospital (descoberto na auditoria de 2026-09); restaurar em
  `~/.config/multicli/` + `~/.config/systemd/user/` se necessário.
