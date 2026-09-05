# Tutorial 00 — Visão geral e acesso

## Os dois servidores

| | **lapan-ai** (hospital) | **lapan-vps** (nuvem) |
|---|---|---|
| Papel | inferência e dados clínicos | porta pública + automação |
| GPU | RTX 5060 Ti 16 GB | — |
| Exposto à internet? | **NÃO** (tudo 127.0.0.1) | sim, só 80/443 via Traefik |
| Acesso | túnel SSH ou tailnet | `https://api.lapan.cloud` / `https://n8n.lapan.cloud` |

Regra de ouro: **dado clínico só no hospital**. O VPS vê metadados
(modelo, tokens, latência), nunca conteúdo de prompts/respostas
(`turn_off_message_logging: true`).

## Serviços e portas (lapan-ai, via túnel)

| Porta | Serviço | O que é |
|---|---|---|
| 3000 | Open WebUI | chat local (frente clínica) |
| 6333/6334 | Qdrant | base vetorial do RAG |
| 7474/7687 | Neo4j | grafo de pesquisa |
| 8000 | Speaches | transcrição de ARQUIVOS (pt-BR) |
| 8010 | WhisperLiveKit | transcrição TEMPO REAL com diarização |
| 8088 | ai-api | gateway OpenAI-compatível com RAG (tailnet: https://lapan-ai.tailf9eac9.ts.net) |
| 8888 | JupyterLab | notebooks |
| 11434 | Ollama | modelos (`gpt-oss:20b` titular) |

## Túnel SSH completo (uma linha, todas as portas)

```bash
ssh -L 3000:127.0.0.1:3000 -L 8888:127.0.0.1:8888 -L 7474:127.0.0.1:7474 \
    -L 7687:127.0.0.1:7687 -L 6333:127.0.0.1:6333 -L 11434:127.0.0.1:11434 \
    -L 8000:127.0.0.1:8000 -L 8010:127.0.0.1:8010 -L 8088:127.0.0.1:8088 \
    hugo@lapan-ai
```

Depois abra no navegador: Open WebUI `http://localhost:3000`, transcrição
realtime `http://localhost:8010`, Jupyter `http://localhost:8888`.

## Caminhos de acesso à IA (do mais simples ao mais programático)

1. **Open WebUI** (túnel) — chat com `gpt-oss:20b`, ditado, prompts de laudo.
2. **n8n** (`https://n8n.lapan.cloud`) — automações: chat "Consulta Drive →
   IA LAPAN", webhooks, agendamentos.
3. **API pública** (`https://api.lapan.cloud/v1`) — para apps próprios,
   com chave virtual. Ver tutoriais 01–03.
4. **Tailnet** (`https://lapan-ai.tailf9eac9.ts.net/v1`) — para nós dentro
   da rede Tailscale, direto no gateway do hospital (com `AI_API_KEY`).

## Segurança em 30 segundos

- Toda chave é **virtual e revogável** (LiteLLM) — nunca distribua a master.
- Segredos vivem nos `.env` dos servidores; backup local em
  `~/Documents/LAPAN/backups/` (nunca no git).
- Tailscale: o hospital não tem porta aberta; o VPS é o único hop público,
   com TLS Let's Encrypt e rate-limit.
