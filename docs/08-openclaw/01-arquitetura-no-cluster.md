# Arquitetura do OpenClaw no Cluster LAPAN

## Visão geral

O OpenClaw roda como um serviço Docker na VM `lapan-ai` (VMID 2020, Ubuntu,
12 vCPU / 26 GiB, GPU RTX 5060 Ti via passthrough), junto com os outros 10
serviços da stack de IA (Ollama, Speaches, Qdrant, Neo4j, ai-api etc.), na
rede interna `lapan-ai-net`.

```text
VM lapan-ai (Proxmox host dedicado)
├─ ollama        LLMs locais (qwen3:8b, gpt-oss:20b, qwen2.5-coder:7b, bge-m3)
├─ qdrant        vector DB (coleção research_chunks_bge_m3)
├─ neo4j         grafo semântico (APOC + GDS)
├─ ai-api        gateway OpenAI-compatível com RAG
└─ openclaw  ◄─── este documento
     ├─ gateway na porta 18789 (bind 127.0.0.1 da VM; acesso via túnel SSH)
     ├─ 9 MCP servers como processos filhos (stdio)
     ├─ searxng (container irmão) para web_search
     └─ volumes: /srv/ai/openclaw/{data,workspace} + raiz de projetos do host
```

## Portas e exposição

- `18789` mapeada em `127.0.0.1` da VM — **nunca** exposta publicamente.
- Acesso pela Control UI via túnel SSH (`ssh -L 18789:127.0.0.1:18789 ...`,
  documentado em `docs/tutorials/13-*`) ou pela rede local confiável
  (`gateway.bind: lan`, `trustedProxies` definidos).

## Volumes (o que persiste e o que não)

| Montagem no container | Conteúdo | Persistência |
| --- | --- | --- |
| `/srv/ai/openclaw/data` → `~/.openclaw` | sessões, memória LanceDB, plugins instalados, config viva | volume na VM (backup incluído) |
| `/srv/ai/openclaw/workspace` → `~/workspace` | AGENTS.md semeado, relatórios `literature-watch/`, `arxiv-papers/` | volume na VM (backup incluído) |
| `/home/hugo/Zotero` → `/home/node/Zotero` | biblioteca Zotero (~5 mil artigos, sqlite + PDFs) | dado do host |
| `/home/hugo/Documents/LAPAN` → `/home/node/host_home` | **raiz de projetos** (dev/, research/, web/...) | dado do host — escopo mínimo |
| `/home/hugo/.config/gh` → `/home/node/gh-config` (ro) | autenticação do `gh` CLI | somente leitura |
| `.gitconfig`, `.git-credentials` (ro), `.gemini`, `.claude` | credenciais/config das CLIs e do git | conforme o compose |

A montagem da home é **deliberadamente restrita à raiz de projetos**
(`~/Documents/LAPAN`): chaves SSH, `.config`, `.gnupg` e o resto da home do
usuário **não** são visíveis para o container. Detalhes e motivação em
[07-seguranca.md](07-seguranca.md).

## O entrypoint (o que acontece no boot)

`entrypoint.sh` roda como PID 1 e, a cada início:

1. **Semeia identidade** — copia `SOUL.md`/`USER.md`/`IDENTITY.md` para
   `~/.openclaw` e `AGENTS.md` + `.markdownlint.jsonc` para o workspace,
   apenas se ainda não existirem (edições locais nunca são sobrescritas;
   atualizar uma identidade versionada exige remover o arquivo do volume).
2. **Instala plugins oficiais ausentes** (`memory-lancedb`, `searxng`,
   `lobster`, `diagnostics-prometheus`, `telegram`) — plugins são stateful no
   volume e por isso não podem ser apenas "assados" na imagem.
3. **Executa o gateway** (`openclaw gateway run`).

## Modelos e cadeia de fallback

Configurados em `models.providers` do `openclaw.json`:

| Provider | Modelos | Uso |
| --- | --- | --- |
| `google` (API) | gemini-2.5-pro, gemini-2.5-flash | titular do agente; flash para subagentes |
| `openrouter` (API) | llama-3.3-70b:free, qwen-2.5-72b:free | primeiro fallback (gratuitos) |
| `ollama` (local) | qwen3:8b, gpt-oss:20b, qwen2.5-coder:7b, gemma4 | fallback final, 100% local |

A cadeia do agente principal: `gemini-2.5-pro` → `llama-3.3-70b:free` →
`qwen3:8b`. Subagentes usam `gemini-2.5-flash` (rápido e barato). As chaves de
API vêm do `.env` via SecretRefs — nada de segredo no git.

## Embeddings locais (bge-m3)

O modelo `bge-m3` do Ollama (1024 dimensões) alimenta **duas** capacidades:

1. a memória de longo prazo (`memory-lancedb`);
2. a busca semântica do MCP `zotero`.

É provisionado por `scripts/openclaw_setup.sh` (`docker exec ollama ollama pull
bge-m3`) — 100% local, sem dado saindo da VM.

## Serviços auxiliares exclusivos do OpenClaw

- **searxng** (container irmão, sem porta exposta): meta-busca web agregando
  Google/Bing/DuckDuckGo via API JSON, consumida pela ferramenta `web_search`
  do plugin `@openclaw/searxng-plugin`. Substitui APIs pagas (Tavily, Brave).

## O fluxo de deploy

```text
repo (git) ──deploy_ai_stack.sh──► /srv/ai/compose/core/  (fonte de build)
                                        │
                              docker compose build openclaw
                                        │
                              docker compose up -d
                                        │
                          entrypoint: seed + plugins + gateway
                                        │
                          openclaw_setup.sh: bge-m3 + automações
```

Referência rápida de operação: [08-operacao-e-manutencao.md](08-operacao-e-manutencao.md).
