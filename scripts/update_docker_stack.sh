#!/usr/bin/env bash
# ==============================================================================
# Script: update_docker_stack.sh
# Descrição: Atualiza com segurança todas as imagens e containers Docker
#            da stack de IA em /srv/ai/compose/core na VM lapan-ai.
#
# Procedimentos executados:
#   1. Auditoria prévia de disco (/ e /srv/ai) e integridade da GPU NVIDIA.
#   2. Backup rápido das configurações (.env e docker-compose.yml).
#   3. Pull de novas versões para imagens oficiais (Ollama, WebUI, Qdrant, Neo4j, Speaches).
#   4. Recompilação com camadas atualizadas dos serviços locais (ai-api, escuta, jupyter, openclaw).
#   5. Recriação dos containers sem interrupção de dados persistentes.
#   6. Limpeza de imagens órfãs (dangling) para liberar espaço.
#   7. Validação automática de saúde e portas via validate_stack.sh.
#
# Uso:
#   ./scripts/update_docker_stack.sh [--no-build] [--no-prune] [--skip-validation]
# ==============================================================================

set -Eeuo pipefail

live_root="${AI_ROOT:-/srv/ai}"
live_compose="${AI_COMPOSE_DIR:-${live_root}/compose/core}"
env_file="${live_compose}/.env"

NO_BUILD=0
NO_PRUNE=0
SKIP_VALIDATION=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-build)
      NO_BUILD=1
      shift
      ;;
    --no-prune)
      NO_PRUNE=1
      shift
      ;;
    --skip-validation)
      SKIP_VALIDATION=1
      shift
      ;;
    -h|--help)
      echo "Uso: $(basename "$0") [--no-build] [--no-prune] [--skip-validation]"
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $1" >&2
      exit 1
      ;;
  esac
done

docker_cmd=(docker)
if ! docker info >/dev/null 2>&1; then
  docker_cmd=(sudo docker)
fi

echo "================================================================="
echo "   Atualização Segura da Stack Docker (lapan-ai)                "
echo "================================================================="

# 1. Auditoria de Espaço em Disco
echo "[1/7] Verificando integridade de disco e GPU..."
if command -v df >/dev/null 2>&1; then
  echo "--- Espaço em disco ---"
  df -h / "${live_root}" || true
fi

if command -v nvidia-smi >/dev/null 2>&1; then
  echo "--- Status da GPU ---"
  nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv,noheader
else
  echo "[!] nvidia-smi não encontrado no PATH direto."
fi

# 2. Backup de segurança das configurações
echo "[2/7] Gerando backup das configurações do Compose..."
backup_dir="${live_root}/backups/compose_pre_update_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${backup_dir}"
if [[ -f "${env_file}" ]]; then
  cp "${env_file}" "${backup_dir}/.env"
fi
if [[ -f "${live_compose}/docker-compose.yml" ]]; then
  cp "${live_compose}/docker-compose.yml" "${backup_dir}/docker-compose.yml"
fi
echo "[+] Configurações salvas em: ${backup_dir}"

# 3. Pull das novas imagens oficiais
echo "[3/7] Baixando novas versões das imagens (docker compose pull)..."
cd "${live_compose}"
"${docker_cmd[@]}" compose --env-file "${env_file}" pull

# 4. Rebuild com base layers atualizadas
if [[ "${NO_BUILD}" -eq 0 ]]; then
  echo "[4/7] Recompilando serviços locais com base layers atualizadas (--pull)..."
  "${docker_cmd[@]}" compose --env-file "${env_file}" build --pull
else
  echo "[4/7] Pulando rebuild de serviços locais (--no-build ativo)."
fi

# 5. Reinicialização dos containers
echo "[5/7] Aplicando atualização dos containers (docker compose up -d)..."
"${docker_cmd[@]}" compose --env-file "${env_file}" up -d

# 6. Limpeza de imagens antigas
if [[ "${NO_PRUNE}" -eq 0 ]]; then
  echo "[6/7] Removendo imagens órfãs/antigas..."
  "${docker_cmd[@]}" image prune -f
else
  echo "[6/7] Pulando limpeza de imagens (--no-prune ativo)."
fi

# 7. Validação da Stack
if [[ "${SKIP_VALIDATION}" -eq 0 ]]; then
  echo "[7/7] Validando integridade dos serviços pós-atualização..."
  repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  if [[ -f "${repo_dir}/scripts/validate_stack.sh" ]]; then
    bash "${repo_dir}/scripts/validate_stack.sh"
  elif [[ -f "/usr/local/sbin/lapan-ai-validate" ]]; then
    sudo -n /usr/local/sbin/lapan-ai-validate
  else
    echo "[!] Script de validação não encontrado no caminho padrão. Verificando containers ativos:"
    "${docker_cmd[@]}" compose --env-file "${env_file}" ps
  fi
else
  echo "[7/7] Validação pulada (--skip-validation ativo)."
fi

echo "================================================================="
echo "[+] Atualização da stack Docker concluída com sucesso!"
echo "================================================================="
