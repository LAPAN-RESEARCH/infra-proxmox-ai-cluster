#!/usr/bin/env bash
set -Eeuo pipefail

live_compose="${AI_COMPOSE_DIR:-/srv/ai/compose/core}"
env_file="${live_compose}/.env"

docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
  docker_cmd=(sudo docker)
fi

require_file() {
  local path="$1"
  [[ -f "${path}" ]] || { echo "Missing required file: ${path}" >&2; exit 1; }
}

require_curl() {
  local label="$1"
  shift
  if "$@" >/dev/null; then
    echo "OK ${label}"
  else
    echo "FAIL ${label}" >&2
    exit 1
  fi
}

require_file "${live_compose}/docker-compose.yml"
require_file "${env_file}"

set -a
# shellcheck disable=SC1090
source "${env_file}"
set +a

speaches_auth_args=()
if [[ -n "${SPEACHES_API_KEY:-}" ]]; then
  speaches_auth_args=(-H "Authorization: Bearer ${SPEACHES_API_KEY}")
fi

echo "== Docker =="
"${docker_cmd[@]}" version --format 'Docker {{.Server.Version}}'
root_dir="$("${docker_cmd[@]}" info --format '{{.DockerRootDir}}')"
echo "Docker Root Dir: ${root_dir}"
[[ "${root_dir}" == "/srv/ai/docker" ]] || { echo "Docker root must be /srv/ai/docker" >&2; exit 1; }

echo "== GPU =="
nvidia-smi --query-gpu=name,memory.total,memory.used --format=csv,noheader
if [[ "${RUN_GPU_CONTAINER_TEST:-0}" == "1" ]]; then
  "${docker_cmd[@]}" run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi >/dev/null
  echo "OK container GPU runtime"
fi

echo "== Compose =="
"${docker_cmd[@]}" compose --env-file "${env_file}" -f "${live_compose}/docker-compose.yml" ps

echo "== HTTP services =="
require_curl "Ollama tags" curl -fsS http://127.0.0.1:11434/api/tags
require_curl "Open WebUI" curl -fsS http://127.0.0.1:3000/health
require_curl "Qdrant collections" curl -fsS -H "api-key: ${QDRANT_API_KEY}" http://127.0.0.1:6333/collections
require_curl "Speaches health" curl -fsS "${speaches_auth_args[@]}" http://127.0.0.1:8000/health
require_curl "Speaches models" curl -fsS "${speaches_auth_args[@]}" http://127.0.0.1:8000/v1/models
require_curl "Jupyter" curl -fsS "http://127.0.0.1:8888/api?token=${JUPYTER_TOKEN}"

curl -fsS http://127.0.0.1:11434/api/tags | grep -q '"name"' || { echo "Ollama returned no model names" >&2; exit 1; }
curl -fsS "${speaches_auth_args[@]}" http://127.0.0.1:8000/v1/models | grep -F "${SPEACHES_MODEL}" >/dev/null || {
  echo "Speaches model is not listed: ${SPEACHES_MODEL}" >&2
  exit 1
}

echo "== Model storage =="
[[ -d /srv/ai/ollama/models ]] || { echo "Missing Ollama model directory: /srv/ai/ollama/models" >&2; exit 1; }
[[ -d /srv/ai/models/huggingface ]] || { echo "Missing Hugging Face model cache: /srv/ai/models/huggingface" >&2; exit 1; }
echo "OK Ollama models stored under /srv/ai/ollama/models"
echo "OK Speaches models cached under /srv/ai/models/huggingface"

echo "== Neo4j =="
neo4j_password="${NEO4J_AUTH#neo4j/}"
"${docker_cmd[@]}" exec neo4j cypher-shell -u neo4j -p "${neo4j_password}" 'RETURN 1 AS ok;' >/dev/null
echo "OK Neo4j cypher-shell"

require_curl "OpenClaw UI" curl -fsS http://127.0.0.1:18789/
if [[ -n "${AI_API_KEY:-}" ]]; then
  require_curl "AI-API health" curl -fsS -H "Authorization: Bearer ${AI_API_KEY}" http://127.0.0.1:8088/healthz
fi

for port in 11434 3000 6333 6334 7474 7687 8888 8000 8020 8088 18789; do
  ss -tln | grep -q "127.0.0.1:${port} " || { echo "Port ${port} is not bound to 127.0.0.1" >&2; exit 1; }
  echo "OK 127.0.0.1:${port}"
done

echo "Stack validation passed."
