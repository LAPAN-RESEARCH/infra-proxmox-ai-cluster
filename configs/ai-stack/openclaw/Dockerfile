FROM node:24-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

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
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir --break-system-packages pymupdf requests httpx pydantic

# Instalar Playwright, OpenClaw e dependências do Chromium headless
RUN npm install -g playwright openclaw@latest clawhub@latest @anthropic-ai/claude-code@latest && \
    npx playwright install-deps chromium && \
    su - node -c "npx playwright install chromium"

COPY --chmod=755 zotero_tool.py /usr/local/bin/zotero

USER node
WORKDIR /home/node/workspace

EXPOSE 18789

CMD ["openclaw", "gateway", "run", "--port", "18789", "--bind", "lan", "--allow-unconfigured"]
