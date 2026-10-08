#!/usr/bin/env bash
set -Eeuo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
live_root="${AI_ROOT:-/srv/ai}"
live_compose="${live_root}/compose/core"
env_file="${live_compose}/.env"

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 32
  else
    od -An -N32 -tx1 /dev/urandom | tr -d ' \n'
  fi
}

append_if_missing() {
  local key="$1"
  local value="$2"
  if [[ ! -f "${env_file}" ]] || ! grep -qE "^${key}=" "${env_file}"; then
    printf '%s=%s\n' "${key}" "${value}" >>"${env_file}"
    echo "Added ${key} to ${env_file}"
  fi
}

mkdir -p \
  "${live_compose}/jupyter" \
  "${live_compose}/openclaw" \
  "${live_root}/backups" \
  "${live_root}/docker" \
  "${live_root}/openclaw/data" \
  "${live_root}/openclaw/workspace" \
  "${live_root}/agents/audit" \
  "${live_root}/agents/clinical" \
  "${live_root}/agents/coding" \
  "${live_root}/agents/graphs" \
  "${live_root}/agents/papers" \
  "${live_root}/agents/policies" \
  "${live_root}/agents/scratch" \
  "${live_root}/ingest/raw" \
  "${live_root}/ingest/parsed" \
  "${live_root}/ingest/chunks" \
  "${live_root}/ingest/metadata" \
  "${live_root}/jupyter/work" \
  "${live_root}/logs/speaches" \
  "${live_root}/models/huggingface" \
  "${live_root}/clinical/audio" \
  "${live_root}/clinical/tmp" \
  "${live_root}/neo4j/data" \
  "${live_root}/neo4j/logs" \
  "${live_root}/neo4j/import" \
  "${live_root}/neo4j/plugins" \
  "${live_root}/neo4j/conf" \
  "${live_root}/ollama" \
  "${live_root}/open-webui" \
  "${live_root}/qdrant/storage" \
  "${live_root}/rag/benchmarks" \
  "${live_root}/rag/configs" \
  "${live_root}/rag/pipelines" \
  "${live_root}/ocr_cache" \
  "${live_root}/evaluations" \
  "${live_root}/inconsistencies" \
  "${live_root}/secrets" \
  "${live_root}/zotero/exports" \
  "${live_root}/zotero/pdfs"


install -m 0644 "${repo_root}/configs/ai-stack/docker-compose.yml" "${live_compose}/docker-compose.yml"
install -m 0644 "${repo_root}/configs/ai-stack/jupyter/Dockerfile" "${live_compose}/jupyter/Dockerfile"

# Contexto de build completo do OpenClaw: Dockerfile, openclaw.json,
# SOUL/AGENTS/USER/IDENTITY.md, zotero_tool.py, entrypoint.sh, mcp-github.sh
# e skills/ — o Dockerfile faz COPY de todos eles.
if [ -d "${repo_root}/configs/ai-stack/openclaw" ]; then
  mkdir -p "${live_compose}/openclaw"
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete --exclude '__pycache__' --exclude '.pytest_cache' \
      "${repo_root}/configs/ai-stack/openclaw/" "${live_compose}/openclaw/"
  else
    cp -a "${repo_root}/configs/ai-stack/openclaw/." "${live_compose}/openclaw/"
  fi
  echo "Synced configs/ai-stack/openclaw -> ${live_compose}/openclaw"
fi

# Config do SearXNG (web_search do OpenClaw), montada pelo compose em ./searxng.
if [ -d "${repo_root}/configs/ai-stack/searxng" ]; then
  mkdir -p "${live_compose}/searxng"
  install -m 0644 "${repo_root}/configs/ai-stack/searxng/searxng-settings.yml" \
    "${live_compose}/searxng/searxng-settings.yml"
fi

install -m 0644 "${repo_root}/configs/ai-stack/rag/research-platform.yaml" "${live_root}/rag/configs/research-platform.yaml"
install -m 0644 "${repo_root}/configs/ai-stack/agents/policies/default.yaml" "${live_root}/agents/policies/default.yaml"


# Serviços com build no compose vivem em ${live_root}/services (convention ai-api).
for svc in ai-api escuta; do
  if [ -d "${repo_root}/services/${svc}" ]; then
    mkdir -p "${live_root}/services/${svc}"
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete --exclude '__pycache__' --exclude '.pytest_cache' \
        "${repo_root}/services/${svc}/" "${live_root}/services/${svc}/"
    else
      cp -a "${repo_root}/services/${svc}/." "${live_root}/services/${svc}/"
    fi
    echo "Synced services/${svc} -> ${live_root}/services/${svc}"
  fi
done

if [[ ! -f "${env_file}" ]]; then
  install -m 0600 "${repo_root}/configs/ai-stack/.env.example" "${env_file}"
  echo "Created ${env_file}; replace placeholder secrets before starting services."
else
  chmod 600 "${env_file}"
fi

append_if_missing "SPEACHES_TAG" "latest-cuda"
append_if_missing "SPEACHES_MODEL" "Systran/faster-distil-whisper-large-v3"
append_if_missing "SPEACHES_API_KEY" "$(generate_secret)"
append_if_missing "OPENCLAW_AUTH_TOKEN" "$(generate_secret)"
append_if_missing "RAG_COLLECTION" "research_chunks_bge_m3"
append_if_missing "RERANKER_MODEL" "BAAI/bge-reranker-v2-m3"
append_if_missing "ESCUTA_PORT" "8020"
append_if_missing "ESCUTA_EXTRAS" "gpu"
append_if_missing "ESCUTA_RETENTION_DAYS" "90"
append_if_missing "ESCUTA_API_TOKEN" "$(generate_secret)"

echo "Deployed Compose source to ${live_compose}"
