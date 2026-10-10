# 08 — OpenClaw: O Agente de IA Pessoal do LAPAN

Esta seção documenta o **OpenClaw**, o agente de IA autônomo que roda no
container `openclaw` da VM `lapan-ai`. Ela foi escrita para quem está começando
nessa stack: cada conceito é explicado antes de ser usado, e cada ferramenta
tem uma seção "para que serve" e "quando usar".

## Índice

| Arquivo | Conteúdo |
| --- | --- |
| [00-conceitos-fundamentais.md](00-conceitos-fundamentais.md) | O que é o OpenClaw e o vocabulário essencial (gateway, agente, sessão, canal, ferramenta, skill, plugin, MCP, subagente, automação, memória) |
| [01-arquitetura-no-cluster.md](01-arquitetura-no-cluster.md) | Como o OpenClaw roda na VM: rede, volumes, portas, entrypoint, modelos de LLM e cadeia de fallback |
| [02-servidores-mcp.md](02-servidores-mcp.md) | Os 9 servidores MCP de pesquisa e código — o que cada um faz, quando usar, exemplos |
| [03-plugins-e-skills.md](03-plugins-e-skills.md) | Plugins oficiais (memória, busca web, pipelines, métricas, Telegram) e a skill GitHub — incluindo como ativar o Telegram passo a passo |
| [04-memoria-e-aprendizado.md](04-memoria-e-aprendizado.md) | Como o agente lembra: LanceDB, embeddings bge-m3 locais, auto-recall/auto-capture e a regra LGPD |
| [05-automacoes.md](05-automacoes.md) | As automações agendadas (varredura de literatura, resumo semanal) e como criar novas |
| [06-codigo-e-subagentes.md](06-codigo-e-subagentes.md) | Engenharia de software: Serena, agy, Claude Code, subagentes nativos e o fluxo recomendado |
| [07-seguranca.md](07-seguranca.md) | Token do gateway, PAT do GitHub, escopo da montagem da home, política de execução e LGPD |
| [08-operacao-e-manutencao.md](08-operacao-e-manutencao.md) | Deploy, pós-deploy, backup, upgrade de versões e troubleshooting |

## Resumo em um parágrafo

O OpenClaw é um **gateway de agentes de IA** open-source que roda na sua
infraestrutura. Ele conecta modelos de LLM (Gemini na nuvem, Qwen/GPT-OSS
locais no Ollama) a **ferramentas** — executar comandos, navegar na web, ler
PDFs, consultar bases acadêmicas via MCP, editar arquivos — e a **canais de
entrada** (hoje a Control UI web; Telegram opcional). O agente do LAPAN é
configurado com uma identidade científica (`SOUL.md`) e instruções de trabalho
(`AGENTS.md`), tem memória de longo prazo local, executa varreduras de
literatura automáticas de madrugada e orquestra subagentes de código
(`agy`, `claude`, Serena) sobre os repositórios do laboratório.

## Onde as configurações vivem

| O quê | Onde (repo) | Onde (VM, após deploy) |
| --- | --- | --- |
| Imagem do container | `configs/ai-stack/openclaw/Dockerfile` | `/srv/ai/compose/core/openclaw/Dockerfile` |
| Config do OpenClaw | `configs/ai-stack/openclaw/openclaw.json` | idem |
| Identidade e instruções | `SOUL.md`, `AGENTS.md`, `USER.md`, `IDENTITY.md` | semeados no volume pelo entrypoint |
| Shims de MCP | `mcp-*.sh` | dentro da imagem (`/usr/local/bin/`) |
| Skills | `skills/` | dentro da imagem (`/opt/openclaw-skills/`) |
| Segredos e chaves | `.env` (não versionado) | `/srv/ai/compose/core/.env` |
| Estado vivo (sessões, memória, plugins) | — (volume) | `/srv/ai/openclaw/data` e `/srv/ai/openclaw/workspace` |

Documentação oficial do OpenClaw: <https://docs.openclaw.ai> — marketplace de
skills/plugins: <https://clawhub.ai>.
