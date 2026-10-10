# Changelog

## 2026-10-10 — OpenClaw P2/P3 + guia completo em português (docs/08-openclaw)

- **MCP `semanticscholar`** (semantic-scholar-mcp 0.4.0, instalação do Hugo):
  grafo de citações e impacto científico; padronizado em shim
  `mcp-semanticscholar.sh` (chave opcional `SEMANTIC_SCHOLAR_API_KEY` via
  `.env`) e regra mandatória de `markdownlint-cli2` no AGENTS/SOUL com config
  `.markdownlint.jsonc` semeada no workspace pelo entrypoint.
- **P2 — Serena MCP** (`serena` via `uv tool install serena-agent`): análise e
  edição de código semântica via LSP (40+ linguagens), entrada `mcp.servers.serena`
  com `--context agent`.
- **P2 — Subagentes nativos**: `agents.defaults.subagents.model` =
  `gemini-2.5-flash` para lanes paralelas; AGENTS.md reorganizado (nativos
  como primeira escolha, CLIs agy/claude para codificação pesada).
- **P2 — Plugins**: `@openclaw/lobster` (pipelines tipados com aprovações —
  IA-as-a-Judge multiestágio) e `@openclaw/diagnostics-prometheus` (métricas
  do runtime) adicionados ao bootstrap idempotente do entrypoint.
- **P2 — Chaves acadêmicas formalizadas** no `.env.example`/compose:
  `PAPER_SEARCH_MCP_SEMANTIC_SCHOLAR_API_KEY`, `PAPER_SEARCH_MCP_OPENALEX_API_KEY`,
  `NCBI_API_KEY` (opcionais, elevam limites de taxa).
- **P3 — Canal Telegram**: plugin `@openclaw/telegram` no bootstrap + slot
  `TELEGRAM_BOT_TOKEN` no `.env`; ativação passo a passo documentada
  (BotFather → channels.telegram → bindings → `--announce` no resumo semanal).
- **P3 — Escopo mínimo da home**: montagem trocada de `/home/hugo` inteiro
  para **`/home/hugo/Documents/LAPAN`** (raiz de projetos) + `~/.config/gh`
  separado em somente-leitura (`GH_CONFIG_DIR=/home/node/gh-config`); chaves
  SSH, `.gnupg` e o resto da home fora do alcance do container. Paths em
  AGENTS/SOUL atualizados para a nova raiz.
- **P3 — Versões pinadas** no Dockerfile via ARG: `OPENCLAW_VERSION=2026.9.9`,
  `CLAWHUB_VERSION=0.23.3`, `CLAUDE_CODE_VERSION=2.1.294`,
  `MARKDOWNLINT_VERSION=0.23.3` (builds reprodutíveis; bump deliberado).
- **Documentação**: nova seção `docs/08-openclaw/` (10 arquivos em português,
  escrita para iniciante): conceitos, arquitetura, 9 MCPs, plugins/skills,
  memória, automações, código/subagentes, segurança (inclui passo a passo do
  PAT fine-grained e a decisão documentada sobre política de exec) e
  operação/troubleshooting; índice adicionado ao README.

## 2026-10-08 — Hardening de envio: segredo do gateway fora do git, backup do OpenClaw e limpeza de config morta

- Token do gateway fora do controle de versão: `openclaw.json` passa a usar
  substituição `${OPENCLAW_GATEWAY_TOKEN}` (formato documentado do OpenClaw) e o
  compose exige `OPENCLAW_AUTH_TOKEN` no `.env` (sintaxe `:?` — o `up` falha com
  mensagem clara em vez de cair no default que estava commitado). O
  `deploy_ai_stack.sh` gera o segredo automaticamente se ausente.
  **Ação do operador:** se o `.env` da VM ainda usa o hex antigo (presente no
  histórico do git), rotacione com `openssl rand -hex 32` no próximo deploy;
  o token do Control UI/túneis muda junto.
- Backup da stack agora cobre o OpenClaw: `openclaw/data` (sessões, memória
  LanceDB, plugins) e `openclaw/workspace` (relatórios literature-watch,
  arxiv-papers) entram no `backup_ai_stack.sh` — antes o agente inteiro ficava
  fora do tar.
- Removido o provider morto `ai-api`/`lapan-judge` do `openclaw.json`: o
  serviço só espelha modelos do Ollama e não existe rota "judge"; a cadeia de
  fallback (gemini-2.5-pro → llama-3.3-70b → qwen3:8b) não o utilizava.

## 2026-10-08 — OpenClaw P0/P1: 7 servidores MCP, memória de longo prazo, busca web local e automações de literatura

- MCP servers no `openclaw.json` (`mcp.servers`): `papers` (paper-search-mcp —
  PubMed/arXiv/bioRxiv/OpenAlex/Semantic Scholar + download OA com fallback),
  `zotero` (zotero-mcp em modo local lendo o `zotero.sqlite` montado, com busca
  semântica via embeddings bge-m3 do próprio Ollama), `arxiv` (leitura por
  seção do LaTeX fonte, watches, citation graph; storage em
  `workspace/arxiv-papers`), `biomcp` (PubMed, ClinicalTrials.gov, ClinVar,
  gnomAD) e `github` (binário oficial v2.0.2 pinado no Dockerfile, toolsets
  restritos a context/repos/issues/pull_requests/actions).
- Dockerfile do OpenClaw: `uv` com `uv tool install` dos 4 MCPs Python como
  binários globais (fail-fast com `command -v`), GitHub CLI do apt oficial,
  binário `github-mcp-server` pinado por `ARG GITHUB_MCP_VERSION`, `entrypoint.sh`
  e shim `mcp-github.sh` (token: PAT do `.env` → fallback oauth_token do
  hosts.yml do gh do host; nenhum segredo no git), skills em
  `/opt/openclaw-skills` e identidade em `/opt/openclaw-identity`.
- Entrypoint idempotente: semeia SOUL/USER/IDENTITY/AGENTS.md no volume na
  primeira execução (corrige o gap de o deploy copiar SOUL.md sem que o
  Dockerfile o entregasse ao runtime) e instala os plugins oficiais ausentes
  (`@openclaw/memory-lancedb`, `@openclaw/searxng-plugin`) — plugins são
  stateful no volume `~/.openclaw`, insuficientes apenas no build.
- Memória de longo prazo: plugin `memory-lancedb` com embeddings **Ollama
  bge-m3** (1024 dims, local, LGPD-friendly), auto-recall + auto-capture;
  `toolSearch: true` reativado para o catálogo ampliado de ferramentas.
- Busca web self-hosted: novo serviço `searxng` na `lapan-ai-net` (mesma config
  da VPS, format JSON habilitado, sem porta exposta) + `web.search.provider:
  searxng`; elimina dependência de APIs pagas.
- `scripts/openclaw_setup.sh` (pós-deploy, na VM): garante `bge-m3` no Ollama e
  cria as automações P1 `varredura-literatura` (dias úteis 06:00) e
  `resumo-semanal-literatura` (segundas 07:00), idempotentes por nome.
- MCPs dos bancos da própria stack: `qdrant` (busca vetorial na coleção
  `research_chunks_bge_m3`) e `neo4j` (Cypher no grafo semântico com
  APOC/GDS), com shims `mcp-qdrant.sh`/`mcp-neo4j.sh` resolvendo
  QDRANT_API_KEY e NEO4J_AUTH do `.env` da stack. Imagem ganha ainda `ruff`,
  `ripgrep`, `fd-find`, `pandoc`, `pymupdf4llm` e `markdownlint-cli2`.
- `deploy_ai_stack.sh`: sincroniza o contexto de build completo do OpenClaw
  (antes copiava só Dockerfile/openclaw.json/SOUL.md e o build falharia no
  `COPY zotero_tool.py`) e instala a config do SearXNG.
- `.env.example`: `GITHUB_PERSONAL_ACCESS_TOKEN` opcional (fine-grained,
  LAPAN-RESEARCH); sem ele o shim reutiliza a auth do gh do host.

## 2026-10-08 — VM 2020 maximizada para o host dedicado (12 vCPUs / 26 GiB)

- Diagnóstico de utilização: host Ryzen 5 5500 (6c/12t, 32 GB) com VM única
  `lapan-ai` em 8 vCPUs/24 GiB — CPU com folga, RAM como gargalo real (guest
  acumulara 5,6 GB em swap).
- Incidente registrado: elevar a VM a 28 GiB via hotplug + `--balloon 0`
  exauriu a RAM do host; o OOM killer matou o processo KVM e host e VM
  ficaram inacessíveis juntos. Recuperação a frio (config aplicada com a VM
  parada) confirmou a causa pelo quadro clássico de OOM.
- Config validada: `cores: 12`, `memory: 26624`, `balloon: 26624` — teto
  seguro para o host de 32 GB (uso base ~2 GB + overhead QEMU). Regras: mudar
  memória apenas com a VM parada; o sinal de pressão é o **swap do host**
  crescendo (não o "livre"); recuo documentado: `24576`.
- Pós-recuperação: os 10 containers da stack de pé, swap do guest zerado,
  inventário Ollama íntegro (8 modelos; artefato `llamacpp:<sha>` que
  duplicava o manifesto do `gpt-oss:20b` removido com
  `docker exec ollama ollama rm llamacpp:<sha>`).
- `docs/06-operations/04-capacity-planning.md`: novo step de teto de RAM do
  host com os comandos de verificação e a regra de recuo.

## 2026-09-26 — Escuta clínica validada ponta a ponta na VM (números reais)

- Infra: kernel atualizado quebrou o driver NVIDIA (módulo era acoplado ao
  kernel 7.0 removido); corrigido com `linux-modules-nvidia-595-server-generic-hwe-26.04`
  (auto-rastreia kernels futuros). Ollama/Speaches/WLK religados.
- Docker sem sudo (grupo `docker`); túnel persistente via systemd user
  (`lapan-tunnels.service`, portas do usuário + 8020).
- `escuta` em produção na porta 8020 (imagem CPU; build GPU com pyannote/ECAPA
  em andamento). Speaches realinhado ao turbo (`deepdml/faster-whisper-large-v3-turbo-ct2`,
  mirror no registry da versão).
- Pipeline LLM: rota nativa Ollama `/api/chat`; decisões de latência —
  **qwen3:8b modelo único** (SOAP+laudo+verificação; `think:false` honrado),
  `num_ctx` 8192 (16k forçava offload CPU do gpt-oss), orçamento 16k com
  salvage de JSON truncado. `ESCUTA_LAUDO_MODEL` permite escalar o laudo no
  batch noturno sem tocar o fluxo do consultório.
- Medição e2e (consulta sintética pt-BR de 60 s, TTS piper): **23 s no total** —
  ASR 6 s (RTF ≈ 0,10), SOAP 4 s, laudo 4 s, verificação 2 s; qwen3:8b
  residente (6,4 GB VRAM) coexistindo com Speaches. Extrapolando: consulta de
  60 min ≈ 7–8 min de processamento.

## 2026-09-24 — Escuta clínica: plano, benchmark ASR e implementação

- Plano arquitetural completo da solução local de escuta clínica com revisão
  de estado da arte 2026 (`docs/00-project-context/07-clinical-listening-solution-plan.md`).
- Decisões registradas: microfone de mesa podcast, retenção de áudio de 90
  dias no piloto, rapidez como gate primário do benchmark, prioridade clínica
  na GPU.
- `scripts/bench_asr.py`: benchmark de RTF/VRAM/WER contra Speaches/WLK com
  corpus sintético pt-BR por TTS (espeak-ng/piper) — valida o pipeline sem a
  sala de gravação.
- Novo serviço `services/escuta/` (porta 8020): app de dois cliques com
  gravação servidor-side e transcrição ao vivo (proxy WLK), worker batch de
  fidelidade (ASR determinístico, diarização pyannote opcional, alinhamento
  palavra×locutor, atribuição Médico/Paciente por tripla checagem), SOAP por
  `gpt-oss:20b` com verificação cruzada (`qwen3:8b`), transcript imutável
  (SQLite WAL + SHA-256), revisão em tela dividida com timestamps clicáveis,
  assinatura com versionamento, lock de GPU clínica-first e expurgo seguro
  após retenção. 31 testes (CPU, backends stub).
- Fix: `benchmark_llm.py` quebrava no Python 3.12 (atributo `_stop` do
  `VramSampler` colidia com `Thread._stop`).

## 2026-05-21 — Validation Pass 1

- Incorporated host-state output from `VMID=2020 scripts/gather_host_state.sh`.
- Incorporated VM-state output from `scripts/gather_vm_state.sh`.
- Confirmed Proxmox VE 9.1.0 on kernel `7.0.2-4-pve`.
- Confirmed Ubuntu Server 26.04 LTS on kernel `7.0.0-15-generic`.
- Confirmed VM disks are on `local-lvm` and Proxmox root usage recovered to 10%.
- Confirmed `/srv/ai` is mounted from `/dev/sdb1` and has 480G available.
- Confirmed RTX 5060 Ti passthrough and NVIDIA guest driver `595.71.05`.
- Confirmed Ollama model inventory: `qwen3:8b`, `qwen2.5-coder:7b`, `bge-m3`, `embeddinggemma`.
- Corrected Jupyter build variable to `JUPYTER_BASE_TAG=2026-05-11`.
- Updated validation scripts to use `sudo docker` fallback and Qdrant API-key-aware checks.

## 2026-05-21

- Accepted Ubuntu Server 26.04 LTS as the working target guest OS.
- Accepted that the VM is online and Docker stack is running by user report.
- Marked previous future roadmap as outdated pending a final validation pass.
- Reorganized documentation into phase-based deployment structure.
- Added state-gathering scripts for Proxmox host and Ubuntu VM.
- Added local-only AI service documentation skeleton and operations guide.
