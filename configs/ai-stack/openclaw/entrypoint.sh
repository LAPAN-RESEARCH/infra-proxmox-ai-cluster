#!/bin/sh
# Bootstrap idempotente do gateway OpenClaw.
#
# 1. Semeia SOUL.md/USER.md/IDENTITY.md em ~/.openclaw e AGENTS.md no workspace
#    na primeira execução (nunca sobrescreve edições locais).
# 2. Instala os plugins oficiais ausentes — plugins são stateful no volume
#    ~/.openclaw e por isso não podem ser instalados apenas no build da imagem.
# 3. Executa o gateway (PID 1).
set -u

OPENCLAW_DIR="${HOME}/.openclaw"
WORKSPACE="${HOME}/workspace"

mkdir -p "${OPENCLAW_DIR}" "${WORKSPACE}/arxiv-papers"

# --- 1. Identidade (primeira execução) ---
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

# --- 2. Plugins oficiais (idempotente) ---
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

# --- 3. Gateway ---
exec openclaw gateway run --port "${OPENCLAW_PORT:-18789}" --bind lan --allow-unconfigured
