# Changelog

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
