#!/usr/bin/env bash
# Clone WhisperLiveKit (pinned ref) to /srv/ai/src and generate its secrets.
# Idempotent: safe to re-run. Docker image build happens via compose
# (`docker compose up -d --build whisper-livekit`), not here.
#
# Usage: bash scripts/install_whisper_livekit.sh          (from the repo or the
#        synced copy on the VM; run as your user, sudo only for docker steps)
set -euo pipefail

WLK_SRC_DIR=${WLK_SRC_DIR:-/srv/ai/src/whisper-livekit}
WLK_REPO_REF=${WLK_REPO_REF:-main}
WLK_REPO_URL=https://github.com/QuentinFuxa/WhisperLiveKit
ENV_FILE=${ENV_FILE:-/srv/ai/compose/core/.env}

umask 077

mkdir -p "$(dirname "$WLK_SRC_DIR")"

if [ ! -d "$WLK_SRC_DIR/.git" ]; then
  echo ">> Cloning WhisperLiveKit ($WLK_REPO_URL @ $WLK_REPO_REF) into $WLK_SRC_DIR"
  git clone "$WLK_REPO_URL" "$WLK_SRC_DIR"
fi

git -C "$WLK_SRC_DIR" fetch --tags
git -C "$WLK_SRC_DIR" checkout "$WLK_REPO_REF"
WLK_COMMIT=$(git -C "$WLK_SRC_DIR" rev-parse --short HEAD)
echo ">> WhisperLiveKit at $WLK_COMMIT"

touch "$ENV_FILE"
if ! grep -q '^WLK_API_TOKEN=' "$ENV_FILE"; then
  echo "WLK_API_TOKEN=$(openssl rand -hex 24)" >> "$ENV_FILE"
  echo ">> Generated WLK_API_TOKEN in $ENV_FILE"
else
  echo ">> WLK_API_TOKEN already present"
fi

echo ">> Done. Next (sudo): cd /srv/ai/compose/core && docker compose up -d --build whisper-livekit"
