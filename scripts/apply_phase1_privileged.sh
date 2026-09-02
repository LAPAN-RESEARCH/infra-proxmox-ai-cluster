#!/usr/bin/env bash
# Consolidated privileged steps for the 2026-09 model/API upgrade on lapan-ai.
# REVIEW then run ON THE VM as root:  sudo bash apply_phase1_privileged.sh
#
# Steps (all reversible; see docs/00-project-context/02-security-model.md):
#  1. Pull latest Ollama image (0.30.7 is too old for qwen3.8) and recreate
#     ollama + speaches with the updated .env:
#     - OLLAMA_KEEP_ALIVE=30m / FLASH_ATTENTION=1 / KV_CACHE_TYPE=q8_0
#     - SPEACHES_MODEL=faster-whisper-large-v3-turbo (multilingual pt-BR;
#       the previous distil model is ENGLISH-ONLY)
#     NOTE (2026-09-02): the running ollama container reports size_vram=0
#     (/api/ps) — inference is silently on CPU. The force-recreate below
#     re-requests `gpus: all`; the script verifies GPU afterwards and prints
#     diagnostics if the container still cannot see the device.
#  2. Build + start whisper-livekit: realtime pt-BR transcription with
#     Sortformer diarization (max 2 speakers) on 127.0.0.1:8010.
#  3. Pull qwen3.8:27b (needs the upgraded Ollama).
#  4. Expose ai-api (127.0.0.1:8088) to the tailnet with automatic TLS:
#     https://lapan-ai.tailf9eac9.ts.net (tailnet-only; nothing public).
#  5. Relaunch the model benchmark (as hugo) with all four candidates.
set -euo pipefail

COMPOSE_DIR=/srv/ai/compose/core
cd "$COMPOSE_DIR"

echo ">> [1/5] Upgrading Ollama image and recreating ollama + speaches"
docker compose pull ollama
docker compose up -d --force-recreate ollama speaches

echo ">> [1/5] GPU check inside the ollama container"
sleep 5
if docker exec ollama nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null; then
  echo "   GPU visível no container."
else
  echo "   !! GPU AUSENTE no container ollama. Diagnóstico:"
  docker info 2>/dev/null | grep -i -A3 "^ *Runtimes:" || true
  echo "   - Confirme nvidia-container-toolkit: 'nvidia-ctk --version' e"
  echo "     'docker info | grep -i nvidia' (deve listar runtime nvidia)."
  echo "   - Se faltar: apt install nvidia-container-toolkit && nvidia-ctk runtime configure --runtime=docker && systemctl restart docker"
fi

echo ">> [2/5] Building and starting whisper-livekit (first build takes a while)"
docker compose up -d --build whisper-livekit

echo ">> [3/5] Waiting for Ollama, then pulling qwen3.8:27b (~18 GB)"
for i in $(seq 1 30); do
  curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1 && break
  sleep 2
done
curl -s -X POST http://127.0.0.1:11434/api/pull -d '{"name":"qwen3.8:27b"}' | tail -c 200; echo

echo ">> [3/5] Verificando que o modelo carrega em VRAM (size_vram > 0)"
curl -s -X POST http://127.0.0.1:11434/api/generate \
  -d '{"model":"qwen3:8b","prompt":"ok","stream":false,"keep_alive":"2m","options":{"num_predict":3}}' >/dev/null
curl -s http://127.0.0.1:11434/api/ps

echo ">> [4/5] Exposing ai-api on the tailnet (tailscale serve, auto TLS)"
tailscale serve --bg 8088 || echo "!! tailscale serve falhou (rodar manual: tailscale serve --bg 8088)"
tailscale serve status 2>/dev/null || true

echo ">> [5/5] Relançando benchmark como hugo (4 modelos)"
runuser -u hugo -- bash -c 'cd ~/benchmark && nohup python3 benchmark_llm.py --cases cases.jsonl --models qwen3:8b gpt-oss:20b gemma4:26b qwen3.8:27b > bench-gpu.log 2>&1 & echo "benchmark pid $!"'

echo
echo ">> Status final"
docker compose ps
echo "Logs: docker compose logs -f whisper-livekit | benchmark: ~/benchmark/bench-gpu.log"
