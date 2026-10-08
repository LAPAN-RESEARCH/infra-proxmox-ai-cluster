---
name: github
description: Opera GitHub via gh CLI nos repositórios da LAPAN-RESEARCH e afins — issues, pull requests, revisão de diffs, execuções de CI (GitHub Actions) e releases. Use quando precisar consultar ou criar issues/PRs, checar o resultado de workflows de qualidade (ruff/mypy/pytest) ou acompanhar deploys.
---

# GitHub via gh CLI

O `gh` está autenticado pelo `GH_CONFIG_DIR` apontando para o hosts.yml do host
(oauth_token herdado). Para operações estruturadas com filtros finos, prefira
as ferramentas MCP do servidor `github`; use o `gh` para tudo o que for
interativo com git local ou quando o MCP não cobrir.

## Padrões dos repositórios LAPAN

- Conventional Commits + Gitmoji; CI = `quality.yml` (ruff → mypy → pytest com
  coverage gate 80%), revisão por IA em `codex-review.yml`, deploy em `deploy.yml`.
- Repos ficam clonados em `/home/node/host_home/Documents/LAPAN/dev/`.

## Comandos frequentes

```bash
# Issues
gh issue list --repo LAPAN-RESEARCH/<repo> --state open
gh issue view <n> --repo LAPAN-RESEARCH/<repo> --comments
gh issue create --repo LAPAN-RESEARCH/<repo> --title "..." --body "..."

# Pull requests
gh pr list --repo LAPAN-RESEARCH/<repo>
gh pr view <n> --repo LAPAN-RESEARCH/<repo> --json title,reviews,statusCheckRollup
gh pr diff <n> --repo LAPAN-RESEARCH/<repo>

# CI (GitHub Actions)
gh run list --repo LAPAN-RESEARCH/<repo> --limit 5
gh run view <id> --repo LAPAN-RESEARCH/<repo> --log-failed

# Releases
gh release list --repo LAPAN-RESEARCH/<repo>
```

Sempre reporte o resultado em pt-BR com o comando executado e o outcome.
