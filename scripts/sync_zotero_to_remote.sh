#!/usr/bin/env bash
# ==============================================================================
# Script: sync_zotero_to_remote.sh
# Descrição: Sincroniza a biblioteca Zotero local (SQLite consistente + PDFs)
#            do notebook para a VM lapan-ai (/home/hugo/Zotero e /srv/ai/zotero).
#
# Destaques de segurança e performance:
#   - Snapshot atômico do SQLite local via sqlite3 .backup (não corrompe WAL)
#   - Exclusão inteligente de backups históricos pesados (*.bak) economizando ~8 GB
#   - Exclusão de arquivos temporários e de bloqueio (*.tmp*, *-wal, *-shm)
#   - Suporte a --dry-run para pré-visualização segura antes de transferir
#   - Validação prévia de conectividade SSH com lapan-ai
#   - Atualização do link simbólico /srv/ai/zotero no servidor
#
# Uso:
#   ./scripts/sync_zotero_to_remote.sh [-n|--dry-run] [--host <ssh_host>]
# ==============================================================================

set -Eeuo pipefail

REMOTE_HOST="${ZOTERO_REMOTE_HOST:-hugo@lapan-ai}"
LOCAL_ZOTERO_DIR="${HOME}/Zotero"
REMOTE_ZOTERO_DIR="/home/hugo/Zotero"
REMOTE_AI_ZOTERO="/srv/ai/zotero"
DRY_RUN=0

print_usage() {
  cat << EOF
Uso: $(basename "$0") [OPÇÕES]

Opções:
  -n, --dry-run     Simula a sincronização sem transferir dados
  -h, --help        Exibe esta mensagem de ajuda
  --host <target>   Alvo SSH (padrão: hugo@lapan-ai)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -n|--dry-run)
      DRY_RUN=1
      shift
      ;;
    --host)
      REMOTE_HOST="$2"
      shift 2
      ;;
    -h|--help)
      print_usage
      exit 0
      ;;
    *)
      echo "Opção desconhecida: $1" >&2
      print_usage
      exit 1
      ;;
  esac
done

echo "================================================================="
echo "   Sincronização Zotero: Local -> Servidor (${REMOTE_HOST})      "
echo "================================================================="

if [[ ! -d "${LOCAL_ZOTERO_DIR}" ]]; then
  echo "[-] Diretório local do Zotero não encontrado em: ${LOCAL_ZOTERO_DIR}" >&2
  exit 1
fi

# 1. Testar conexão SSH
echo "[1/5] Testando conectividade SSH com ${REMOTE_HOST}..."
if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${REMOTE_HOST}" "echo OK" >/dev/null 2>&1; then
  echo "[-] ERRO: Não foi possível conectar a ${REMOTE_HOST}." >&2
  echo "    Certifique-se de que a máquina lapan-ai está ligada e acessível via Tailscale ou LAN." >&2
  exit 1
fi
echo "[+] Conexão SSH confirmada com sucesso!"

# 2. Preparar diretórios remotos
echo "[2/5] Garantindo diretórios no servidor..."
if [[ "${DRY_RUN}" -eq 0 ]]; then
  ssh "${REMOTE_HOST}" "mkdir -p '${REMOTE_ZOTERO_DIR}' '${REMOTE_AI_ZOTERO}/exports' '${REMOTE_AI_ZOTERO}/pdfs' 2>/dev/null || true"
else
  echo "    [dry-run] Criaria diretórios em ${REMOTE_ZOTERO_DIR} e ${REMOTE_AI_ZOTERO}"
fi

# 3. Snapshot consistente do banco de dados SQLite
TMP_DB="$(mktemp -u /tmp/zotero_snapshot_XXXXXX.sqlite)"
echo "[3/5] Gerando snapshot atômico do banco zotero.sqlite..."
if command -v sqlite3 >/dev/null 2>&1; then
  sqlite3 "file:${LOCAL_ZOTERO_DIR}/zotero.sqlite?immutable=1" ".backup '${TMP_DB}'"
  echo "    Snapshot gerado com segurança em: ${TMP_DB} ($(du -h "${TMP_DB}" | cut -f1))"
else
  echo "[!] Aviso: sqlite3 não instalado. Copiando zotero.sqlite diretamente (feche o Zotero se puder)."
  cp "${LOCAL_ZOTERO_DIR}/zotero.sqlite" "${TMP_DB}"
fi

# 4. Sincronização via rsync dos anexos e arquivos de tradutores/estilos
echo "[4/5] Sincronizando dados e arquivos de anexo (storage/)..."
RSYNC_FLAGS="-avz --progress --human-readable"
if [[ "${DRY_RUN}" -eq 1 ]]; then
  RSYNC_FLAGS="${RSYNC_FLAGS} --dry-run"
fi

rsync ${RSYNC_FLAGS} \
  --exclude='*.bak' \
  --exclude='*.tmp*' \
  --exclude='*-wal' \
  --exclude='*-shm' \
  --exclude='zotseek.sqlite*' \
  --exclude='fulltext.sqlite*' \
  "${LOCAL_ZOTERO_DIR}/" \
  "${REMOTE_HOST}:${REMOTE_ZOTERO_DIR}/"

# 5. Enviar o snapshot SQLite consistente
echo "[5/5] Enviando banco de dados SQLite consistente..."
if [[ "${DRY_RUN}" -eq 0 ]]; then
  scp "${TMP_DB}" "${REMOTE_HOST}:${REMOTE_ZOTERO_DIR}/zotero.sqlite"
  rm -f "${TMP_DB}"

  # Atualizar link simbólico no /srv/ai/zotero se permissões permitirem
  ssh "${REMOTE_HOST}" "
    if [ -w '${REMOTE_AI_ZOTERO}' ]; then
      ln -sfn '${REMOTE_ZOTERO_DIR}/storage' '${REMOTE_AI_ZOTERO}/storage'
      ln -sfn '${REMOTE_ZOTERO_DIR}/zotero.sqlite' '${REMOTE_AI_ZOTERO}/zotero.sqlite'
    fi
  "
  echo "================================================================="
  echo "[+] Sincronização concluída com sucesso no servidor!"
  echo "================================================================="
else
  rm -f "${TMP_DB}"
  echo "================================================================="
  echo "[+] Simulação (--dry-run) finalizada sem erros!"
  echo "================================================================="
fi
