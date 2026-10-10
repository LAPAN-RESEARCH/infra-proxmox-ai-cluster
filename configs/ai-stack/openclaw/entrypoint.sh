#!/bin/sh
# Bootstrap idempotente do gateway OpenClaw.
#
# 1. Semeia SOUL.md/USER.md/IDENTITY.md em ~/.openclaw e AGENTS.md no workspace
#    na primeira execução (nunca sobrescreve edições locais).
# 3. Instala os plugins oficiais ausentes — plugins são stateful no volume
#    ~/.openclaw e por isso não podem ser instalados apenas no build da imagem.
# 4. Executa o gateway (PID 1).
set -u

OPENCLAW_DIR="${HOME}/.openclaw"
WORKSPACE="${HOME}/workspace"

mkdir -p "${OPENCLAW_DIR}" "${WORKSPACE}/arxiv-papers"

# --- 1. Config declarativa (sempre) + identidade (primeira execução) ---
# O openclaw.json do repo é a fonte da verdade: sobrepõe a cópia do volume a
# cada boot (o runtime pode regravar o arquivo, mas o repo vence no próximo
# início). Estado vivo — sessões, memória, plugins, automações — vive fora
# dele e não é tocado.
if [ -f /opt/openclaw-config/openclaw.json ]; then
  cp /opt/openclaw-config/openclaw.json "${OPENCLAW_DIR}/openclaw.json"
  echo "[entrypoint] openclaw.json sincronizado (fonte: imagem/repo)"
fi
# --- 2. Identidade (primeira execução) ---
for f in SOUL.md USER.md IDENTITY.md; do
  if [ -f "/opt/openclaw-identity/${f}" ] && [ ! -f "${OPENCLAW_DIR}/${f}" ]; then
    cp "/opt/openclaw-identity/${f}" "${OPENCLAW_DIR}/${f}"
    echo "[entrypoint] seeded ${OPENCLAW_DIR}/${f}"
  fi
done
if [ -f "/opt/openclaw-identity/AGENTS.md" ] && [ ! -f "${WORKSPACE}/AGENTS.md" ]; then
  cp "/opt/openclaw-identity/AGENTS.md" "${WORKSPACE}/AGENTS.md"
  echo "[entrypoint] seeded ${WORKSPACE}/AGENTS.md"
fi
if [ -f "/opt/openclaw-identity/.markdownlint.jsonc" ] && [ ! -f "${WORKSPACE}/.markdownlint.jsonc" ]; then
  cp "/opt/openclaw-identity/.markdownlint.jsonc" "${WORKSPACE}/.markdownlint.jsonc"
  echo "[entrypoint] seeded ${WORKSPACE}/.markdownlint.jsonc"
fi

# --- 3. Plugins oficiais (idempotente) ---
ensure_plugin() {
  pkg="$1"
  id="$2"
  if openclaw plugins list 2>/dev/null | grep -q "${id}"; then
    echo "[entrypoint] plugin ${id} já instalado"
  else
    echo "[entrypoint] instalando ${pkg}..."
    if ! openclaw plugins install "${pkg}" --accept-capabilities 2>&1; then
      echo "[entrypoint] aviso: falha ao instalar ${pkg}; instale manualmente com"
      echo "[entrypoint]   docker exec -it openclaw openclaw plugins install ${pkg}"
    fi
  fi
}

# Memória de longo prazo (embeddings Ollama bge-m3) e busca web self-hosted.
ensure_plugin "@openclaw/memory-lancedb" "memory-lancedb"
ensure_plugin "@openclaw/searxng-plugin" "searxng"
# Pipelines tipados com aprovações (IA-as-a-Judge multiestágio).
ensure_plugin "@openclaw/lobster" "lobster"
# Métricas Prometheus do runtime (sessions, tokens, falhas de MCP).
ensure_plugin "@openclaw/diagnostics-prometheus" "diagnostics-prometheus"
# Canal Telegram: plugin instalado, mas só ativa com channels.telegram no
# openclaw.json + TELEGRAM_BOT_TOKEN (ver docs/08-openclaw/03-plugins-e-skills.md).
ensure_plugin "@openclaw/telegram" "telegram"

# --- 4. Gateway ---
exec openclaw gateway run --port "${OPENCLAW_PORT:-18789}" --bind lan --allow-unconfigured
