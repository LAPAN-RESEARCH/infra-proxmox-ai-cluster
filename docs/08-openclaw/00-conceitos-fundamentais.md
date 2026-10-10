# Conceitos Fundamentais do OpenClaw

Este arquivo explica o vocabulário que aparece em toda a documentação e na
configuração. Leia-o primeiro se você nunca trabalhou com agentes de IA.

## O que é o OpenClaw

O OpenClaw é um **gateway de agentes pessoais** open-source. Na prática, ele é
um servidor que:

1. recebe pedidos seus (pela interface web **Control UI**, por um **canal**
   como Telegram, ou por uma **automação** agendada);
2. entrega o pedido a um **agente** — um loop de LLM que pensa, escolhe
   **ferramentas**, executa e responde;
3. devolve a resposta no mesmo canal de entrada.

A diferença para um chatbot comum (ChatGPT, Gemini web) é que o agente **age**:
roda comandos, lê e escreve arquivos, consulta bancos de dados acadêmicos,
abre páginas web e delega trabalho para outros programas — tudo dentro dos
limites que você configurou.

## O vocabulário essencial

### Gateway

O processo central do OpenClaw (`openclaw gateway run`). É ele que escuta na
porta 18789, autentica pelo token, gerencia sessões, agências e canais. No
LAPAN ele roda como PID 1 do container `openclaw`, iniciado pelo
`entrypoint.sh`.

### Agente

A "personalidade" configurada que atende os pedidos. Um agente tem:

- **modelo** — qual LLM usa (no LAPAN: `gemini-2.5-pro`, com fallbacks);
- **workspace** — o diretório onde trabalha (`/home/node/workspace`);
- **instruções** — `SOUL.md` (identidade e valores), `AGENTS.md` (regras
  operacionais), `USER.md` (quem é o usuário).

### Sessão

Uma conversa com começo, meio e histórico próprio. Sessões isoladas (usadas
pelas automações) nascem limpas a cada execução e morrem depois; a sessão
principal (`main`) acumula o contexto das suas conversas pela Control UI.

### Canal (channel)

A porta de entrada/saída de mensagens: Control UI (web, embutida), Telegram
(plugin instalado, opcional), WhatsApp, Discord etc. O LAPAN usa hoje apenas a
Control UI via túnel SSH — o Telegram é opcional e documentado em
[03-plugins-e-skills.md](03-plugins-e-skills.md).

### Ferramenta (tool)

Uma capacidade que o modelo pode invocar durante o raciocínio: `exec` (rodar
comandos), `read`/`write`/`edit` (arquivos), `web_search` (busca via SearXNG),
`browser` (navegador Playwright), `memory_recall` (memória), e todas as
ferramentas vindas de MCP servers e plugins. O OpenClaw filtra quais
ferramentas o modelo enxerga por chamada — com `toolSearch` ativado, o modelo
pesquisa no catálogo grande em vez de receber todos os esquemas de uma vez.

### MCP (Model Context Protocol)

Um padrão aberto para plugar ferramentas externas em agentes de IA. Um
**servidor MCP** é um programa que expõe um conjunto de ferramentas
estruturadas (com nome, descrição e parâmetros tipados). O OpenClaw inicia
esses servidores como processos filhos (transporte *stdio*) ou conecta a
servidores remotos (HTTP). No LAPAN temos 9 servidores MCP — ver
[02-servidores-mcp.md](02-servidores-mcp.md).

**MCP vs. `exec` bruto:** com `exec`, o agente lê a saída de um comando
qualquer; com MCP, ele recebe ferramentas com contrato estável — mais
confiável, mais barato em tokens e mais fácil de auditar. Por isso o
`AGENTS.md` manda preferir MCP quando existir.

### Skill

Um **pacote de instruções** (pasta com `SKILL.md` e arquivos de apoio) que
ensina o agente a fazer algo — por exemplo, operar o GitHub via `gh` CLI.
Skills não são programas: são conhecimento versionado. As skills do LAPAN
vivem em `configs/ai-stack/openclaw/skills/` e são carregadas na imagem em
`/opt/openclaw-skills/` (config `skills.load.extraDirs`).

### Plugin

Um **pacote de código** (npm) que estende o OpenClaw em si — adiciona canais
(Telegram), provedores de busca (SearXNG), memória (LanceDB), pipelines
(Lobster) ou métricas (Prometheus). Plugins são instalados em runtime no
volume `~/.openclaw` (o `entrypoint.sh` instala os oficiais de forma
idempotente) e configurados em `plugins.entries` no `openclaw.json`.

### Subagente

Um agente-filho spawnado durante uma execução para trabalhar em paralelo
(pesquisar X enquanto revisa Y). Roda em sessão própria, com modelo próprio
(no LAPAN: `gemini-2.5-flash`), e devolve o resultado ao pai. Não confundir
com as CLIs `agy`/`claude`, que são programas externos invocados via `exec` —
ver [06-codigo-e-subagentes.md](06-codigo-e-subagentes.md).

### Automação (cron)

Um agendamento persistente: "às 06:00 em dias úteis, envie este prompt ao
agente em sessão isolada". Gerado por `openclaw automations add`, vive no
gateway (volume), e registra histórico de execuções. O LAPAN tem duas — ver
[05-automacoes.md](05-automacoes.md).

### Memória de longo prazo

Fatos persistidos entre sessões, armazenados num banco vetorial local
(LanceDB) e recuperados por similaridade semântica antes de cada turno.
Ver [04-memoria-e-aprendizado.md](04-memoria-e-aprendizado.md).

### Control UI

A interface web embutida do gateway (`http://<host>:18789`), com chat, gestão
de sessões, plugins, MCP, automações e configuração. No LAPAN só é alcançável
por túnel SSH ou rede local — nunca exposta à internet.

## Como uma mensagem flui

```text
Você (Control UI / Telegram / automação)
  └─> Gateway (porta 18789, autentica pelo token)
        └─> Agente (LLM: gemini-2.5-pro → fallbacks)
              ├─ pensa (reasoning) e escolhe ferramentas
              ├─ MCP papers / zotero / arxiv / biomcp / github / ...
              ├─ web_search (SearXNG) / browser / exec / memory_recall
              ├─ (opcional) subagentes em paralelo
              └─ responde no canal de origem
```

## Onde configurar o quê

| Quero mudar... | Edite |
| --- | --- |
| Modelos, fallbacks, servidor MCP, plugins, skills | `configs/ai-stack/openclaw/openclaw.json` |
| Identidade/personalidade do agente | `SOUL.md` |
| Regras de trabalho e uso das ferramentas | `AGENTS.md` |
| Programas instalados na imagem | `Dockerfile` |
| Segredos (tokens, chaves de API) | `.env` da stack (nunca no git) |
| Variáveis de ambiente do container | `docker-compose.yml` (serviço `openclaw`) |
| Agendamentos | `openclaw automations` (CLI, no container) |

Depois de qualquer mudança versionada, o fluxo é: `deploy_ai_stack.sh` →
`docker compose build openclaw` → `up -d` (detalhes em
[08-operacao-e-manutencao.md](08-operacao-e-manutencao.md)).
