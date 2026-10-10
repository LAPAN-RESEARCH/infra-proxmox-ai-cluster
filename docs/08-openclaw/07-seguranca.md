# Segurança do OpenClaw

Este documento consolida o modelo de ameaças e as salvaguardas do agente. Ele
existe porque o agente combina três coisas perigosas quando mal configuradas:
**execução arbitrária de comandos**, **acesso a credenciais** e **leitura de
conteúdo não confiável** (papers da internet).

## Princípio geral

O agente tem poder real — é o propósito (engenharia autônoma). O que a
arquitetura faz é **limitar o raio de dano**: escopos mínimos de montagem,
segredos fora do git, autenticação obrigatória e superfícies de rede fechadas.

## Superfície de rede

- Gateway em `127.0.0.1:18789` na VM — acesso só por túnel SSH ou rede local
  confiável (`trustedProxies` explícitos). Nada publicado na VPS.
- SearXNG e MCPs são internos à rede `lapan-ai-net`, sem portas expostas.
- Dado clínico (`/srv/ai/clinical`, escuta) é **totalmente invisível** ao
  container do OpenClaw.

## Autenticação do gateway

Token obrigatório (`OPENCLAW_AUTH_TOKEN` no `.env`, sintaxe `:?` no compose —
o stack nem sobe sem ele; `deploy_ai_stack.sh` gera um se ausente). O
`openclaw.json` referencia por substituição `${OPENCLAW_GATEWAY_TOKEN}`.
**Histórico:** um token antigo ficou commitado no git; foi removido e o
`.env` rotacionado — se a VM ainda usa o hex antigo, rotacione (ver CHANGELOG
de 2026-10-08).

## Credenciais e escopos

| Credencial | Como chega ao container | Escopo |
| --- | --- | --- |
| git (`~/.gitconfig`, `.git-credentials`) | montagem `ro` | push/pull nos repos do Hugo |
| gh CLI (`~/.config/gh`) | montagem `ro` (`/home/node/gh-config`) | conta GitHub do Hugo (OAuth) |
| GitHub MCP | PAT opcional `.env` → fallback token gh | toolsets: leitura + issues/PRs/actions |
| Gemini/OpenRouter | `.env` via SecretRefs | APIs de LLM |
| Zotero | leitura do sqlite montado | biblioteca (somente leitura na prática) |

### Recomendação: PAT fine-grained dedicado (pendente de adoção)

Crie um token **só para o agente**, escopado à org `LAPAN-RESEARCH`
(permissions: Contents R/W, Issues R/W, Pull requests R/W, Actions R), e
coloque no `.env`:

```text
GITHUB_PERSONAL_ACCESS_TOKEN=github_pat_...
```

Assim o shim para de usar o OAuth da sua conta pessoal — se o agente vazar
credencial, o raio de dano são os repos do laboratório, não sua conta.
Passo a passo: GitHub → Settings → Developer settings → Fine-grained tokens →
Generate → *Resource owner*: LAPAN-RESEARCH → *Repository access*: org only.

## Montagem da home (escopo mínimo)

O container vê **apenas** `/home/hugo/Documents/LAPAN` (rw, raiz de projetos) —
não enxerga `~/.ssh` (chaves privadas, incluindo a do convênio HOLHOS),
`~/.gnupg`, `~/.config` (exceto o `gh` montado ro), downloads, e-mail etc.
Essa foi a mudança de hardening de 2026-10: antes a home inteira era montada.

## Conteúdo não confiável e prompt injection

Papers, páginas web e saídas de MCP são **entrada não confiável**: podem
conter instruções maliciosas ("ignore as regras anteriores..."). Salvaguardas:

1. Identidade forte (`SOUL.md`) que trata fonte externa como dado, não ordem.
2. `autoCapture` da memória filtra payloads de injeção; incognito pula tudo.
3. O raio de dano é limitado pelos escopos acima (a lição prática: mantenha-os).
4. Não exponha canais públicos sem pareamento (`dmPolicy: pairing` no
   Telegram) nem sem revisar permissões por canal.

## Política de execução (decisão documentada)

Hoje: `exec.security: full`, `ask: off` — autonomia total, coerente com a
missão "Non-Stop" do SOUL.md. A política aspiracional
(`configs/ai-stack/agents/policies/default.yaml`) prevê allowlist + revisão
humana; os documentos de contexto do laboratório recomendam shell autônomo
**fora** de contexto clínico. **Como apertar, se um dia for necessário:**
`tools.exec` aceita modo `sandboxed` com aprovações (`ask`) — o custo é
interromper o fluxo autônomo. A decisão é do laboratório; este documento
registra o trade-off.

## LGPD

- Nenhum dado clínico identificável em: memória LanceDB (regra do SOUL.md),
  workspace, automações, canais.
- Embeddings e inferência de memória/subagentes-texto podem rodar 100% locais
  (Ollama) — o tráfego de LLM para nuvem (Gemini) recebe apenas texto de
  trabalho sem identificadores.
- Retenção: sessões e memória no volume da VM; backup cobre `openclaw/data` e
  `openclaw/workspace` (restore implica revisar conteúdo LGPD antes).

## Checklist pós-incidente (se suspeitar de comprometimento)

1. `docker exec openclaw openclaw sessions list` — procure sessões estranhas.
2. Rotacione: `OPENCLAW_AUTH_TOKEN`, `GITHUB_PERSONAL_ACCESS_TOKEN` (se
   usado), PATs do git (`gh auth refresh`), chaves de API do `.env`.
3. Revise diffs dos repos: `git log --since` em cada projeto montado.
4. Reconstrua o volume se necessário (imagem é reprodutível; estado volta do
   backup).
