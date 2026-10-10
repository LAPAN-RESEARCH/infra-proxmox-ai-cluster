# Plugins e Skills

**Regra de bolso:** *skill* ensina (instruções), *plugin* adiciona código ao
OpenClaw (canais, memória, busca, métricas). Plugins oficiais são instalados
automaticamente pelo `entrypoint.sh` no primeiro boot e configurados em
`plugins.entries` do `openclaw.json`.

## Plugins instalados

### memory-lancedb — memória de longo prazo

Ocupa o *slot* `memory` (só um plugin por slot). Embeddings **locais** via
Ollama (`bge-m3`, 1024 dims) — nada sai da VM. Ferramentas expostas:
`memory_recall`, `memory_store`, `memory_forget`; CLI: `openclaw ltm list |
search | stats`. Detalhes em [04-memoria-e-aprendizado.md](04-memoria-e-aprendizado.md).

### searxng — busca web self-hosted

Provedor da ferramenta `web_search`, apontando para o container `searxng`
interno (sem chave de API, sem custo). Aceita `categories` por chamada — use
`science` para literatura. Seleção do provedor em `tools.web.search.provider`.

### lobster — pipelines tipados com aprovações

Ferramenta de orquestração para fluxos multiestágio com **checkpoints** — o
agente pode montar um pipeline (ex.: varredura → triagem → veredito → revisão
humana) que pausa para aprovação e retoma de onde parou. Encaixa no padrão
IA-as-a-Judge do laboratório: etapas determinísticas separadas do julgamento.

### diagnostics-prometheus — métricas do runtime

Exporta métricas Prometheus (sessões, tokens, latências, falhas de MCP) para
scrape. Ainda não há um Prometheus servidor na stack — o plugin fica pronto;
quando houver, basta apontar o scraper. Alternativa: `diagnostics-otel`
(telemetria OpenTelemetry).

### telegram — canal de mensagens (opcional)

Plugin instalado e **desativado por padrão** (não há `channels.telegram` no
`openclaw.json`). Quando ativado, você conversa com o agente pelo Telegram e as
automações podem te notificar (`--announce --channel telegram`).

#### Como ativar (passo a passo)

1. No Telegram, fale com **@BotFather** → `/newbot` → escolha nome e username
   → copie o token (`123456:ABC-...`).
2. Coloque o token no `.env` da stack:

   ```bash
   TELEGRAM_BOT_TOKEN=123456:ABC-seu-token
   ```

3. Adicione ao `openclaw.json` (repo) o bloco do canal e o binding:

   ```json
   {
     "channels": {
       "telegram": {
         "enabled": true,
         "botToken": "${TELEGRAM_BOT_TOKEN}",
         "dmPolicy": "pairing"
       }
     },
     "bindings": [
       { "agentId": "main", "match": { "channel": "telegram", "accountId": "default" } }
     ]
   }
   ```

4. Redeploy (`deploy_ai_stack.sh` + `compose up -d`) e mande um `/hi` para o
   bot. `dmPolicy: pairing` exige pareamento na primeira conversa — só quem
   tiver o código fala com o agente.

Para que o resumo semanal de literatura chegue no Telegram, edite a automação:
`openclaw automations edit resumo-semanal-literatura --announce --channel
telegram --to <seu_chat_id>`.

**Por que Telegram e não WhatsApp:** o canal WhatsApp do OpenClaw usa a
API web não-oficial (risco de banimento do número) e, no contexto LGPD do
laboratório, um número dedicado de bot é mais limpo que o WhatsApp pessoal.

## Skills

Skills são pastas com `SKILL.md` (frontmatter `name` + `description`) carregadas
de `/opt/openclaw-skills/` (config `skills.load.extraDirs`) — versionadas no
repo, sem estado no volume.

### github (skill própria)

Ensina o agente a operar os repositórios LAPAN-RESEARCH com o `gh` CLI
(autenticado via `GH_CONFIG_DIR` → config do gh do host, somente leitura):
issues, PRs, diffs, execuções de CI, releases — incluindo os padrões do lab
(Conventional Commits, `quality.yml` com ruff→mypy→pytest). Complementa o MCP
`github` para o que é interativo com git local.

### Como adicionar uma skill nova

1. Crie `configs/ai-stack/openclaw/skills/<nome>/SKILL.md` com frontmatter e
   instruções (conciso — skills entram no contexto do agente).
2. Commit + deploy + rebuild: a pasta é copiada para a imagem no build.

Skills da comunidade podem ser instaladas via ClawHub
(`clawhub skill install <autor>/<slug>`) — instalam no volume `~/.openclaw`,
fora do controle de versão; prefira versionar skills críticas no repo.
Marketplace: <https://clawhub.ai>.

## Gestão

```bash
# plugins instalados e estado
sudo docker exec openclaw openclaw plugins list

# instalar/remover manualmente
sudo docker exec openclaw openclaw plugins install @openclaw/<nome>
sudo docker exec openclaw openclaw plugins remove <id>

# Config UI: http://localhost:18789 (túnel) → Settings → Plugins / MCP
```

O `entrypoint.sh` reinstala plugins oficiais ausentes a cada boot — remover um
plugin oficial exige também removê-lo da lista do entrypoint.
