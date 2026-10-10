#!/bin/sh
# Wrapper do servidor MCP oficial do GitHub (github-mcp-server).
#
# Resolve o token nesta ordem, mantendo segredos fora do git:
#   1. GITHUB_PERSONAL_ACCESS_TOKEN do ambiente do container (.env da stack)
#   2. oauth_token do hosts.yml do gh CLI montado do host (somente-leitura)
#   3. vazio — o servidor sobe e as chamadas retornam erro de autenticação
#
# Toolsets restritos a leitura + issues/PRs/Actions; push continua sendo feito
# pelo git (com as credenciais já montadas), não pelo MCP.
: "${GITHUB_PERSONAL_ACCESS_TOKEN:=$(sed -n 's/^[[:space:]]*oauth_token:[[:space:]]*//p' \
  "${GH_CONFIG_DIR:-/home/node/gh-config}/hosts.yml" 2>/dev/null | head -n1)}"
export GITHUB_PERSONAL_ACCESS_TOKEN
export GITHUB_TOOLSETS="${GITHUB_TOOLSETS:-context,repos,issues,pull_requests,actions}"

exec /usr/local/bin/github-mcp-server stdio
