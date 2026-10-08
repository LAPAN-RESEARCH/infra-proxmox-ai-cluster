# Whisper Transcription Service

## 1. Objective & Prerequisites

- Add local speech-to-text for consultation transcription using Speaches, an OpenAI-compatible server backed by faster-whisper.
- Required previous state: Docker, NVIDIA runtime, and `/srv/ai` are working.
- Estimated time: 10-30 minutes plus model download time. Risk level: medium due to medical privacy and GPU use.

## 2. Step-by-Step Execution

### Step 1: Deploy and start Speaches

- **Purpose:** Make Whisper transcription available as a local API.
- **Command(s):**

```bash
scripts/install_whisper_service.sh
```

- **Explanation:** The script syncs Compose config, adds missing Speaches `.env` keys, pulls `ghcr.io/speaches-ai/speaches:latest-cuda`, and starts only the `speaches` service.
- **Expected Output:**

```text
Speaches is healthy at http://127.0.0.1:8000
Speaches model is available: Systran/faster-distil-whisper-large-v3
```

- **Verification:** Authenticated `/health` succeeds, `/v1/models` lists `${SPEACHES_MODEL}`, and `/srv/ai/models/huggingface` is not empty.
- **⚠️ Caveats/Traps:** The model download uses Hugging Face during first startup; do this before a real consultation.

### Step 2: Validate file transcription

- **Purpose:** Confirm the OpenAI-compatible transcription endpoint works before live use.
- **Command(s):**

```bash
source /srv/ai/compose/core/.env
curl -fsS \
  -H "Authorization: Bearer ${SPEACHES_API_KEY}" \
  http://127.0.0.1:8000/v1/audio/transcriptions \
  -F "file=@/path/to/test-audio.wav" \
  -F "model=${SPEACHES_MODEL}"
```

- **Expected Output:**

```text
{"text":"..."}
```

- **Verification:** The returned text matches the test audio closely enough for your workflow.
- **⚠️ Caveats/Traps:** Do not upload patient audio to a cloud transcription service; use this local endpoint through SSH tunnel or localhost.

### Step 3: Use realtime transcription

- **Purpose:** Support live consultation transcription.
- **Command(s):**

```bash
source /srv/ai/compose/core/.env
echo "Realtime URL: ws://127.0.0.1:8000/v1/realtime?model=${SPEACHES_MODEL}&intent=transcription&api_key=${SPEACHES_API_KEY}"
```

- **Explanation:** Speaches exposes an OpenAI-compatible realtime WebSocket API with a transcription-only mode.
- **Expected Output:**

```text
Realtime URL: ws://127.0.0.1:8000/v1/realtime?...
```

- **Verification:** A client can stream microphone audio and receive transcription events.
- **⚠️ Caveats/Traps:** Realtime quality depends on microphone placement, room noise, language, GPU availability, and the chosen model.

## 3. Configuration Files

Live `.env` keys:

```env
SPEACHES_TAG=latest-cuda
SPEACHES_MODEL=Systran/faster-distil-whisper-large-v3
SPEACHES_API_KEY=${REPLACE_WITH_RANDOM_HEX}
```

Persistent model cache:

```text
/srv/ai/models/huggingface
```

Speaches service source:

```text
configs/ai-stack/docker-compose.yml
```

## 4. Troubleshooting & Recovery

- If startup is slow, check `sudo docker compose logs --tail=100 speaches`; the first run may be downloading the model.
- If `/v1/models` is empty, run `scripts/install_whisper_service.sh`; it downloads `${SPEACHES_MODEL}` through the Speaches model API and waits for it to be listed.
- If transcription is slow, stop competing GPU workloads or choose a smaller `SPEACHES_MODEL`.
- If the endpoint returns `401`, include `Authorization: Bearer ${SPEACHES_API_KEY}`.
- If a consultation transcript may contain patient data, keep it local, restrict file permissions, and do not paste logs or transcripts into public systems.
