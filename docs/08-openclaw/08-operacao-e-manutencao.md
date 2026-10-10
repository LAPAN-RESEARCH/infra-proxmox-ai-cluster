# Operação e Manutenção do OpenClaw

## Deploy completo (a partir do repo)

No host de desenvolvimento (repo `infra-proxmox-ai-cluster`):

```bash
./scripts/deploy_ai_stack.sh
```

Na VM `lapan-ai`:

```bash
cd /srv/ai/compose/core
sudo docker compose build openclaw
sudo docker compose up -d
```

Pós-deploy (uma vez por deploy, idempotente):

```bash
scripts/openclaw_setup.sh   # bge-m3 no Ollama + automações de literatura
```

## Verificação de saúde

```bash
sudo docker compose ps                                    # serviços de pé
sudo docker exec openclaw openclaw mcp status --verbose   # 9 servidores MCP
sudo docker exec openclaw openclaw plugins list           # 5+ plugins
sudo docker exec openclaw openclaw automations list       # 2 automações
sudo docker logs openclaw --tail 50                       # entrypoint + gateway
```

Sinais de problema no log do boot: `[entrypoint] aviso: falha ao instalar`
(plugin da ClawHub fora do ar — reinstale manualmente depois), ou linhas de
substituição não resolvida (`${...}`) indicando variável faltando no `.env`.

## Backup

`scripts/backup_ai_stack.sh` inclui `openclaw/data` (sessões, memória,
plugins) e `openclaw/workspace` (relatórios, arxiv-papers), além do `.env`
redacted. O estado é restaurável: imagem reprodutível (versões pinadas) +
volumes do backup.

## Upgrade de versão

As versões npm estão **pinadas** no Dockerfile por ARG — upgrade deliberado:

```dockerfile
ARG OPENCLAW_VERSION=2026.9.9   # bump aqui
```

1. Consulte o changelog do OpenClaw (<https://docs.openclaw.ai>) por breaking
   changes (o `openclaw doctor` ajuda a migrar config).
2. Bump do ARG no repo → commit → deploy → rebuild → `docker exec openclaw
   openclaw doctor`.
3. Os MCPs Python sobem junto (latest no build); se um `mcp doctor --probe`
   reclamar de um servidor específico após rebuild, pinar também aquele
   pacote (`uv tool install 'pacote==versão'`).

## Rotinas periódicas

| Frequência | Rotina | Comando |
| --- | --- | --- |
| Diária (automática) | varredura de literatura | automação `varredura-literatura` |
| Semanal (automática) | resumo executivo | automação `resumo-semanal-literatura` |
| Semanal | checar discos (arxiv-papers cresce) | `du -sh /srv/ai/openclaw/workspace` |
| Mensal | backup restore-test + rotação de segredos | `backup_ai_stack.sh` + revisar `.env` |

## Troubleshooting comum

| Sintoma | Causa provável | Ação |
| --- | --- | --- |
| `compose up` falha pedindo `OPENCLAW_AUTH_TOKEN` | `.env` sem o token | `openssl rand -hex 32` no `.env` da VM |
| MCP `papers`/`semanticscholar` com rate limit | chaves opcionais ausentes | preencher no `.env` (ver `.env.example`) |
| GitHub MCP: erro 401 | PAT inválido/expirado ou gh sem auth no host | revisar `GITHUB_PERSONAL_ACCESS_TOKEN` ou `gh auth status` no host |
| Zotero MCP: banco travado | Zotero desktop sincronizando no momento | aguardar; leitura usa snapshot (5 s) |
| Serena lento na primeira query | download do language server | normal na 1ª análise de cada projeto |
| Gateway não responde | container reiniciando (log do entrypoint) | `docker logs openclaw`; conferir `.env` |
| Plugin não instalado | ClawHub fora do ar no boot | `docker exec openclaw openclaw plugins install @openclaw/<pkg>` |

## Mudar a identidade do agente (SOUL/AGENTS)

Os arquivos são **semeados no volume na primeira execução** e não são
sobrescritos. Para aplicar uma nova versão vinda do repo:

```bash
# na VM — remova a cópia viva; o entrypoint semeia a nova no próximo boot
sudo rm /srv/ai/openclaw/data/SOUL.md          # ou workspace/AGENTS.md
sudo docker compose restart openclaw
```

Edições rápidas podem ser feitas direto no volume, mas serão divergentes do
git — trate o repo como fonte da verdade.

## Onde pedir ajuda

- Docs oficiais: <https://docs.openclaw.ai> (comece por `doctor` e `mcp`).
- Marketplace e skills: <https://clawhub.ai>.
- Logs do container são a primeira fonte de verdade: `docker logs openclaw`.
