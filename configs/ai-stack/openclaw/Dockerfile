FROM node:24-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# uv com ferramentas e cache em paths globais: os binários MCP ficam disponíveis
# para o usuário `node` e sobrevivem à troca de usuário no build.
ENV UV_LINK_MODE=copy \
    UV_TOOL_DIR=/usr/local/share/uv-tools \
    UV_TOOL_BIN_DIR=/usr/local/bin \
    UV_CACHE_DIR=/usr/local/share/uv-cache \
    UV_PYTHON_INSTALL_DIR=/usr/local/share/uv-python

# Versão pinada do servidor MCP oficial do GitHub (binário Go standalone).
ARG GITHUB_MCP_VERSION=v2.0.2

# Versões pinadas dos pacotes npm — builds reprodutíveis; bump deliberado via
# ARG (o openclaw.json registra a versão tocada em meta.lastTouchedVersion).
ARG OPENCLAW_VERSION=2026.9.9
ARG CLAWHUB_VERSION=0.23.3
ARG CLAUDE_CODE_VERSION=2.1.294
ARG MARKDOWNLINT_VERSION=0.23.3

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    jq \
    curl \
    ffmpeg \
    ca-certificates \
    sqlite3 \
    python3 \
    python3-pip \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-por \
    poppler-utils \
    libgl1 \
    pandoc \
    ripgrep \
    fd-find \
    && rm -rf /var/lib/apt/lists/*

# GitHub CLI (skill github + uso direto via exec), do repositório apt oficial.
RUN curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      -o /usr/share/keyrings/githubcli-archive-keyring.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" \
      > /etc/apt/sources.list.d/github-cli.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends gh \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages pymupdf pymupdf4llm requests httpx pydantic uv

# MCP servers acadêmicos e de dados (paper-search, zotero, arxiv, biomcp,
# qdrant, neo4j, semantic-scholar), Serena (LSP semântico p/ código) e ruff
# como binários globais — fail-fast com `command -v` para garantir disponibilidade.
RUN uv tool install paper-search-mcp \
    && uv tool install zotero-mcp-server \
    && uv tool install arxiv-mcp-server \
    && uv tool install biomcp-cli \
    && uv tool install mcp-server-qdrant \
    && uv tool install mcp-neo4j-cypher \
    && uv tool install --with "mcp<2" semantic-scholar-mcp \
    && uv tool install serena-agent \
    && uv tool install ruff \
    && command -v paper-search-mcp zotero-mcp arxiv-mcp-server biomcp mcp-server-qdrant mcp-neo4j-cypher semantic-scholar-mcp serena ruff

# Servidor MCP oficial do GitHub (Go), pinado por ARG.
RUN curl -fsSL \
      "https://github.com/github/github-mcp-server/releases/download/${GITHUB_MCP_VERSION}/github-mcp-server_Linux_x86_64.tar.gz" \
      -o /tmp/ghmcp.tar.gz \
    && mkdir -p /tmp/ghmcp \
    && tar -xzf /tmp/ghmcp.tar.gz -C /tmp/ghmcp \
    && find /tmp/ghmcp -type f -name github-mcp-server -exec install -m 0755 {} /usr/local/bin/github-mcp-server \; \
    && rm -rf /tmp/ghmcp /tmp/ghmcp.tar.gz \
    && github-mcp-server --help > /dev/null

# Instalar Playwright, OpenClaw, Markdownlint e dependências do Chromium headless
RUN npm install -g \
      openclaw@${OPENCLAW_VERSION} \
      clawhub@${CLAWHUB_VERSION} \
      @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION} \
      markdownlint-cli2@${MARKDOWNLINT_VERSION} \
      playwright \
    && npx playwright install-deps chromium \
    && su - node -c "npx playwright install chromium"

COPY --chmod=755 zotero_tool.py /usr/local/bin/zotero
COPY --chmod=755 mcp-github.sh /usr/local/bin/mcp-github
COPY --chmod=755 mcp-neo4j.sh /usr/local/bin/mcp-neo4j
COPY --chmod=755 mcp-qdrant.sh /usr/local/bin/mcp-qdrant
COPY --chmod=755 mcp-semanticscholar.sh /usr/local/bin/mcp-semanticscholar
COPY --chmod=755 entrypoint.sh /usr/local/bin/entrypoint.sh
COPY --chmod=644 SOUL.md AGENTS.md USER.md IDENTITY.md .markdownlint.jsonc /opt/openclaw-identity/
COPY skills/ /opt/openclaw-skills/

USER node
WORKDIR /home/node/workspace

EXPOSE 18789

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
