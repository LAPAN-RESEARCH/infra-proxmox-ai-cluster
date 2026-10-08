#!/usr/bin/env bash
# Pós-deploy das ferramentas P0/P1 do OpenClaw (executar NA VM lapan-ai,
# depois de `deploy_ai_stack.sh` + `docker compose up -d`).
#
# 1. Garante o modelo de embeddings bge-m3 no Ollama (memória de longo prazo
#    memory-lancedb e busca semântica do zotero-mcp).
# 2. Cria as automações de varredura de literatura (idempotente por nome).
#
# Uso: scripts/openclaw_setup.sh
set -Eeuo pipefail

OPENCLAW_CONTAINER="${OPENCLAW_CONTAINER:-openclaw}"
OLLAMA_CONTAINER="${OLLAMA_CONTAINER:-ollama}"
TZ="${TZ:-America/Sao_Paulo}"

echo "==> Embeddings bge-m3 no Ollama (memória + busca semântica Zotero)"
if docker exec "${OLLAMA_CONTAINER}" ollama list 2>/dev/null | grep -q '^bge-m3'; then
  echo "    bge-m3 já presente"
else
  docker exec "${OLLAMA_CONTAINER}" ollama pull bge-m3
fi

# `openclaw automations add` em builds recentes; `create` em builds antigos.
automation_add() {
  if docker exec "${OPENCLAW_CONTAINER}" openclaw automations --help 2>/dev/null \
      | grep -qE '(^|[[:space:]])add([[:space:]]|$)'; then
    docker exec "${OPENCLAW_CONTAINER}" openclaw automations add "$@"
  else
    docker exec "${OPENCLAW_CONTAINER}" openclaw automations create "$@"
  fi
}

automation_exists() {
  docker exec "${OPENCLAW_CONTAINER}" openclaw automations list 2>/dev/null \
    | grep -q "$1"
}

ensure_automation() {
  local name="$1"; shift
  if automation_exists "${name}"; then
    echo "    automação '${name}' já existe"
  else
    automation_add --name "${name}" "$@"
    echo "    automação '${name}' criada"
  fi
}

echo "==> Automações de literatura (P1)"

# Varredura matinal em dias úteis: busca -> triagem IA-as-a-Judge -> relatório.
ensure_automation "varredura-literatura" \
  --cron "0 6 * * 1-5" \
  --tz "${TZ}" \
  --session isolated \
  --message 'Varredura diária de literatura LAPAN. Use as ferramentas do servidor MCP "papers" (busca em PubMed, arXiv, bioRxiv, OpenAlex, últimos resultados) e "arxiv" para publicações novas sobre: oculomics; eletroretinografia; TDAH/dislexia e déficit magnocelular; IA clínica em oftalmologia; adaptação/tradução de instrumentos de saúde. Triagem com o rigor IA-as-a-Judge do SOUL.md (descarte amostras mínimas, claims sem controle). Salve relatório em /home/node/workspace/literature-watch/AAAA-MM-DD.md com: artigos relevantes (título, DOI, fonte, justificativa de 1 linha) e os elegíveis para leitura profunda. Se não houver novidades, registre "sem novidades". Não pertube o usuário.'

# Resumo executivo semanal (segundas 07:00) dos relatórios da semana.
ensure_automation "resumo-semanal-literatura" \
  --cron "0 7 * * 1" \
  --tz "${TZ}" \
  --session isolated \
  --message 'Compile os relatórios de /home/node/workspace/literature-watch/ dos últimos 7 dias em um resumo executivo: top 5 achados com veredito de evidência (STRONG_EVIDENCE/QUALIFIED_SUPPORT/WEAK_EVIDENCE/UNFOUNDED_OVERCLAIM) e 1 ação recomendada para o laboratório. Salve em /home/node/workspace/literature-watch/semana-AAAA-SS.md e apresente a síntese ao usuário.'

echo "==> Estado final"
docker exec "${OPENCLAW_CONTAINER}" openclaw automations list 2>/dev/null || true
echo "Concluído. Para desativar uma automação: docker exec ${OPENCLAW_CONTAINER} openclaw automations remove <job-id>"
