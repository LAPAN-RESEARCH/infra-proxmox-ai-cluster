#!/usr/bin/env bash
# Backup local de segredos, envs e configs dos servidores LAPAN.
# Escopo (decisão 2026-09-03): segredos + configs + dumps; SEM dados grandes
# (modelos são re-pulláveis; Qdrant/Neo4j/ingest ficam de fora por padrão).
#
# Uso: bash scripts/backup_secrets.sh
# Destino: ~/Documents/LAPAN/backups/secrets-AAAAMMDD-HHMM/ (permissão 700,
# fora do repositório — NUNCA commitar este diretório).
#
# Requer: ssh hugo@lapan-ai (sem sudo) e ssh root@lapan-vps.
# O backup do Open WebUI (dados root-owned) precisa de um sudo SEU — o script
# imprime o comando pronto no final.
set -euo pipefail

DEST="${DEST:-$HOME/Documents/LAPAN/backups/secrets-$(date +%Y%m%d-%H%M)}"
HOSP=hugo@lapan-ai
VPS=root@lapan-vps

mkdir -p "$DEST"/{lapan-ai,lapan-vps,snapshots}
chmod 700 "$DEST"
umask 077   # arquivos 600, diretórios 700

echo ">> Destino: $DEST"

echo ">> [1/3] lapan-ai (hospital)"
mkdir -p "$DEST/lapan-ai/compose-core" "$DEST/lapan-ai/multicli" "$DEST/lapan-ai/benchmark"
scp -q "$HOSP:/srv/ai/compose/core/.env"                          "$DEST/lapan-ai/compose-core/"
scp -q "$HOSP:/srv/ai/compose/core/docker-compose.yml"            "$DEST/lapan-ai/compose-core/"
scp -q "$HOSP:/srv/ai/compose/core/jupyter/Dockerfile"            "$DEST/lapan-ai/compose-core/" 2>/dev/null || true
scp -q "$HOSP:/srv/ai/rag/configs/research-platform.yaml"         "$DEST/lapan-ai/" 2>/dev/null || true
scp -q "$HOSP:.config/multicli/env" "$HOSP:.config/multicli/manifest.json" \
        "$HOSP:.config/multicli/launcher.sh"                      "$DEST/lapan-ai/multicli/" 2>/dev/null \
  || echo "   (multicli ausente — ok se não existir)"
scp -q "$HOSP:.config/systemd/user/multicli.service"              "$DEST/lapan-ai/multicli/" 2>/dev/null || true
scp -q "$HOSP:benchmark/run-bench.sh"                             "$DEST/lapan-ai/benchmark/" 2>/dev/null || true
scp -q "$HOSP:benchmark/bench-final.log"                          "$DEST/lapan-ai/benchmark/" 2>/dev/null || true
scp -q -r "$HOSP:benchmark/benchmark-results"                     "$DEST/lapan-ai/benchmark/" 2>/dev/null || true

ssh "$HOSP" 'curl -s http://127.0.0.1:11434/api/tags; echo; curl -s http://127.0.0.1:11434/api/ps; echo; tailscale serve status; echo; ss -tln' \
  > "$DEST/snapshots/lapan-ai-state.txt" 2>&1 || echo "   (snapshot hospital parcial)"

echo ">> [2/3] lapan-vps"
mkdir -p "$DEST/lapan-vps/n8n-files"
scp -q "$VPS:/srv/vps/.env"                                       "$DEST/lapan-vps/"
scp -q "$VPS:/srv/vps/docker-compose.yml"                         "$DEST/lapan-vps/"
scp -q "$VPS:/srv/vps/litellm-config.yaml"                        "$DEST/lapan-vps/"
scp -q "$VPS:/srv/vps/searxng-settings.yml"                       "$DEST/lapan-vps/" 2>/dev/null || true
scp -q "$VPS:/srv/vps/n8n/files/n8n-cred.json"                    "$DEST/lapan-vps/n8n-files/"
scp -q "$VPS:/srv/vps/n8n/files/n8n-wf.json"                      "$DEST/lapan-vps/n8n-files/"
scp -q "$VPS:/srv/vps/n8n/data/config"                            "$DEST/lapan-vps/n8n-files/n8n-config" 2>/dev/null || true
ssh "$VPS" 'cat /var/lib/docker/volumes/survey_traefik_letsencrypt/_data/acme.json' \
  > "$DEST/lapan-vps/acme.json"

ssh "$VPS" 'docker exec lapan-postgres pg_dump -U lapan litellm' > "$DEST/lapan-vps/pg_litellm.sql"
ssh "$VPS" 'docker exec lapan-postgres pg_dump -U lapan n8n'     > "$DEST/lapan-vps/pg_n8n.sql"
ssh "$VPS" 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"; echo; docker network ls; echo; docker exec lapan-postgres psql -U lapan -d litellm -c "SELECT key_alias, blocked, spend, max_budget, rpm_limit FROM \"LiteLLM_VerificationToken\" ORDER BY key_alias;"' \
  > "$DEST/snapshots/lapan-vps-state.txt" 2>&1 || echo "   (snapshot VPS parcial)"

echo ">> [3/3] Manifest"
cat > "$DEST/MANIFEST.md" <<EOF
# Backup de segredos LAPAN — $(date '+%F %R')

Gerado por scripts/backup_secrets.sh. Conteúdo e origem exata de cada artefato:

## lapan-ai/ (hospital)
- compose-core/.env — TODOS os segredos do hospital (WEBUI_SECRET_KEY,
  QDRANT_API_KEY, NEO4J_AUTH, JUPYTER_TOKEN, SPEACHES_API_KEY, AI_API_KEY,
  WLK_API_TOKEN, runtime OLLAMA_*). Restaurar em /srv/ai/compose/core/.env (chmod 600).
- compose-core/docker-compose.yml + jupyter/Dockerfile — deploy vivo.
- research-platform.yaml — /srv/ai/rag/configs/.
- multicli/ — serviço local do usuário (~/.config/multicli + unit systemd).
- benchmark/ — suíte, logs e resultados.

## lapan-vps/
- .env — POSTGRES_PASSWORD, LITELLM_MASTER_KEY, LITELLM_SALT_KEY,
  N8N_ENCRYPTION_KEY, LAPAN_AI_API_KEY (cópia da AI_API_KEY do hospital),
  SANDBOX_*, SEARXNG_SECRET, DOMAIN. Restaurar em /srv/vps/.env (chmod 600, root).
- docker-compose.yml + litellm-config.yaml — deploy vivo (também no repo).
- searxng-settings.yml — VERSÃO COM SECRET REAL INLINE (a do repo é template).
- n8n-files/n8n-cred.json — credencial Google Drive (client id/secret).
- n8n-files/n8n-wf.json — workflow com a chave virtual real do n8n.
- n8n-files/n8n-config — instanceId do n8n.
- acme.json — certificados Let's Encrypt do Traefik (permissão 600!).
- pg_litellm.sql / pg_n8n.sql — dumps COMPLETOS (chaves virtuais, budgets,
  credenciais n8n cifradas, workflows). Restaurar com:
  cat pg_litellm.sql | docker exec -i lapan-postgres psql -U lapan litellm
  (idem n8n; restaurar APÓS criar os bancos via init-dbs.sh).

## snapshots/
- Estado de portas, modelos, serve do tailscale, containers e inventário de
  chaves — para auditoria, não para restauração.

## Fora do escopo (existem mas não estão aqui)
- /root/survey/.env e .env.vps, /root/edu-neurovision-ppgmec (outros projetos).
- Dados: /srv/ai/{ollama,models,qdrant,neo4j,ingest,zotero,open-webui} —
  modelos são re-pulláveis; o Open WebUI precisa do sudo abaixo.

## PENDENTE MANUAL: Open WebUI (root-owned)
Rodar e depois mover o .tgz para este diretório:
  ssh -t hugo@lapan-ai 'sudo tar czf /tmp/open-webui-\$(date +%Y%m%d).tgz -C /srv/ai/open-webui . && sudo chown hugo /tmp/open-webui-*.tgz'
  scp hugo@lapan-ai:/tmp/open-webui-*.tgz $DEST/lapan-ai/
EOF

chmod -R go-rwx "$DEST"
echo
echo ">> Concluído. Resumo:"
du -sh "$DEST"/{lapan-ai,lapan-vps,snapshots} 2>/dev/null
echo
echo ">> PRÓXIMOS PASSOS MANUAIS:"
echo "   1) Backup do Open WebUI (comando sudo no MANIFEST.md acima)"
echo "   2) NUNCA commitar este diretório; considerar cópia externa cifrada (gpg -c)"
