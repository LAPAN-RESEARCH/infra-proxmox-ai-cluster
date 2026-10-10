# Código e Subagentes

O agente LAPAN é também um engenheiro de software autônomo. Há três
mecanismos, em ordem crescente de peso:

## 1. Serena (MCP) — entendimento semântico de código

Para *entender e localizar* antes de mudar: busca de símbolos, referências,
implementações e refatoração no nível de símbolo via LSP (Python e
TypeScript cobrem praticamente todo o portfólio do laboratório). Perguntas
típicas: "onde `process_erg` é chamado no erg_analysis?", "quais classes
implementam `BaseWriter`?". Baixa language servers sob demanda na primeira
análise de um projeto.

## 2. Subagentes nativos — paralelismo com isolamento

A ferramenta `subagents`/`sessions_spawn` cria agentes-filho em sessão
própria, com modelo próprio (`gemini-2.5-flash` via
`agents.defaults.subagents.model`), que devolvem o resultado ao pai. Use para
lanes paralelas de tamanho médio: auditar um módulo, revisar um diff, resumir
um conjunto de papers — trabalho que não precisa do contexto inteiro da
conversa nem de uma CLI pesada.

## 3. CLIs especializadas — codificação pesada

Invocadas via `exec` a partir da raiz de projetos
(`/home/node/host_home` = `~/Documents/LAPAN` do Hugo):

| CLI | Perfil | Invocação |
| --- | --- | --- |
| `agy` (Antigravity) | arquitetura, refatoração profunda, análise multimodal | `cd <projeto> && agy --dangerously-skip-permissions -p "<objetivo>"` |
| `claude` (Claude Code) | implementação cirúrgica, scripts, testes | `cd <projeto> && claude --dangerously-skip-permissions -p "<objetivo>"` |

Ambas rodam com as permissões do usuário Hugo dentro da raiz de projetos, com
suas credenciais próprias montadas (`.gemini`, `.claude`). O
`--dangerously-skip-permissions` é o modo não-interativo — consequência
direta de operar sem humano no circuito; os limites vêm do escopo de montagem
(Ver [07-seguranca.md](07-seguranca.md)).

## Fluxo recomendado para uma tarefa de código

```text
1. Entender     → serena: símbolos, referências, impacto da mudança
2. Planejar     → o agente propõe o plano (arquivos, testes afetados)
3. Executar     → claude (mudanças cirúrgicas) ou agy (refatoração ampla)
4. Verificar    → exec: ruff, pytest, gh run watch (CI)
5. Relatar      → síntese com arquivos tocados + comandos + resultado
```

Padrões do laboratório que o agente deve respeitar (da skill `github` e do
`lab-guidelines`): Conventional Commits, `quality.yml` (ruff → mypy → pytest
com coverage ≥ 80%), `uv` como gestor de dependências, CITATION.cff em todos
os repos.

## Ferramentas de apoio na imagem

| Ferramenta | Uso |
| --- | --- |
| `ruff` | lint/format Python (o mesmo do CI) |
| `markdownlint-cli2` | qualidade de Markdown — **regra mandatória** do AGENTS.md para qualquer `.md` produzido |
| `pandoc` | conversões Markdown ↔ LaTeX ↔ PDF |
| `ripgrep` / `fd-find` | busca rápida em código e nomes |
| `gh` | GitHub CLI (autenticado via `GH_CONFIG_DIR`) |
| `zotero` (CLI próprio) | busca/leitura de PDFs com OCR |

## Limites e boas práticas

- Mudanças em repos são feitas **de fato** (git commit/push via credenciais
  montadas). Para trabalho exploratório, prefira pedir um branch.
- CI é o freio de qualidade: sempre checar `gh run list` após push.
- Para datasets clínicos, nenhum código deve tocar os volumes de dado clínico
  (`/srv/ai/clinical`) — o container do OpenClaw nem os enxerga.
