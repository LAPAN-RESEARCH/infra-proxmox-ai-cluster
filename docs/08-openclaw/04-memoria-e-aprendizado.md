# Memória e Aprendizado de Longo Prazo

## O problema que a memória resolve

LLMs são sem estado: sem memória, toda sessão começa do zero e o agente
reaprende que "o Hugo prefere respostas em tabela" todos os dias. A memória de
longo prazo persiste **fatos** entre sessões e os injeta de volta no contexto
quando são relevantes.

## Como funciona no LAPAN

O plugin `@openclaw/memory-lancedb` armazena os fatos num banco vetorial local
(LanceDB, em `~/.openclaw/memory/lancedb`). O ciclo:

```text
antes do turno:  texto atual → embedding bge-m3 (Ollama local) → busca por
                 similaridade → memórias relevantes entram no contexto (auto-recall)
depois do turno: fatos novos → memory_store → ficam disponíveis para sempre
```

Configuração relevante (`openclaw.json` → `plugins.entries.memory-lancedb`):

| Opção | Valor no LAPAN | Efeito |
| --- | --- | --- |
| `embedding.provider` | `ollama` (`bge-m3`, 1024 dims) | 100% local, LGPD-friendly |
| `autoRecall` | `true` | memórias relevantes entram sozinhas |
| `autoCapture` | `true` | até 3 fatos por turno são capturados (com dedupe e filtro anti-injection) |
| `recallMaxChars` | 1000 (default) | limite de contexto injetado |

## O que vale a pena memorizar

**Sim:** decisões de arquitetura do laboratório ("preferimos uv a pip"),
preferências do Hugo, lições metodológicas de revisões ("o dataset X tem
vazamento temporal no split original"), atalhos operacionais.

**Não:** dados clínicos identificáveis (LGPD — regra explícita no SOUL.md),
segredos, conteúdo volátil. Sessões *incognito* pulam recall e captura.

## Ferramentas e CLI

O agente usa `memory_store` / `memory_recall` / `memory_forget`. Você opera
pela CLI:

```bash
sudo docker exec openclaw openclaw ltm list          # tudo que foi lembrado
sudo docker exec openclaw openclaw ltm search "rCCA" # busca por similaridade
sudo docker exec openclaw openclaw ltm stats         # volume da memória
```

## Relação com as outras "memórias" da stack

| Mecanismo | O que guarda | Quem usa |
| --- | --- | --- |
| Memória LanceDB (este doc) | fatos operacionais do agente | o agente OpenClaw |
| Sessões do gateway | histórico completo de conversas | transcript e auditoria |
| Qdrant `research_chunks_bge_m3` | chunks dos PDFs ingeridos | RAG (ai-api, MCP qdrant) |
| Zotero sqlite | bibliografia | MCP zotero, CLI zotero |
| `literature-watch/` no workspace | relatórios das varreduras | automações e consultas |

Não confunda: a memória LanceDB não indexa papers — para isso existem Qdrant e
Zotero. Ela guarda o que o agente *aprendeu sobre o trabalho*.

## Manutenção

- Trocar o modelo de embedding (`provider`/`model`/`dimensions`) muda a
  identidade do índice: memories antigas não são re-embutidas — planeje rebuild
  (`openclaw ltm` exporta/re-importa) se um dia trocar o bge-m3.
- O dado vive no volume `~/.openclaw` → já coberto pelo `backup_ai_stack.sh`
  (`openclaw/data`).
