#!/usr/bin/env bash
set -Eeuo pipefail

ai_root="${AI_ROOT:-/srv/ai}"
backup_dir="${BACKUP_DIR:-${ai_root}/backups}"
stamp="$(date -u +%Y%m%d-%H%M%S)"
archive="${backup_dir}/ai-stack-${stamp}.tar.gz"
tmp_dir="$(mktemp -d)"

cleanup() {
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

mkdir -p "${backup_dir}"
mkdir -p "${tmp_dir}/redacted"

if [[ -f "${ai_root}/compose/core/.env" ]]; then
  sed -E 's/^(.*(SECRET|TOKEN|KEY|AUTH).*)=.*/\1=<redacted>/' \
    "${ai_root}/compose/core/.env" >"${tmp_dir}/redacted/compose.env"
fi

tar -czf "${archive}" \
  --exclude='ollama' \
  --exclude='docker' \
  --exclude='models/huggingface' \
  --exclude='clinical/tmp' \
  -C "${ai_root}" \
  agents \
  clinical \
  compose/core/docker-compose.yml \
  compose/core/jupyter/Dockerfile \
  openclaw/data \
  openclaw/workspace \
  open-webui \
  qdrant \
  neo4j \
  jupyter/work \
  rag \
  zotero/exports \
  -C "${tmp_dir}" \
  redacted

echo "Wrote ${archive}"
