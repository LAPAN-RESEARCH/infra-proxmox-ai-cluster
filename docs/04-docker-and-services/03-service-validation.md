# Service Validation

### 1. Objective & Prerequisites

- Validate Docker, GPU runtime, AI service bindings, and model inventory.
- Required previous state: Compose stack started.
- Estimated time: 5-15 minutes. Risk level: low.

### 2. Step-by-Step Execution

**Step 1: Validate Docker with permission handling**

- **Purpose:** Confirm Docker works even when the user is not in the Docker group.
- **Command(s):**

```bash
sudo docker version
sudo docker info | grep 'Docker Root Dir'
```

- **Explanation:** The validated VM produced permission errors when running plain `docker`; this is acceptable if `sudo docker` works.
- **Expected Output:**

```text
Docker Engine - Community
Version: 29.5.2
Docker Root Dir: /srv/ai/docker
```

- **Verification:** Docker root must be `/srv/ai/docker`.
- **⚠️ Caveats/Traps:** Adding a user to the Docker group is root-equivalent; using `sudo docker` is the safer default.

**Step 2: Validate GPU runtime**

- **Purpose:** Confirm containers can see the GPU.
- **Command(s):**

```bash
nvidia-smi
sudo docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

- **Expected Output:**

```text
NVIDIA-SMI 595.71.05
NVIDIA GeForce RTX 5060 Ti
```

- **Verification:** Both commands show the GPU.
- **⚠️ Caveats/Traps:** Host driver validation and container runtime validation are separate checks.

**Step 3: Validate Ollama**

- **Purpose:** Confirm model server is running and models are present.
- **Command(s):**

```bash
curl -fsS http://127.0.0.1:11434/api/tags
```

- **Expected Output:**

```text
embeddinggemma:latest
bge-m3:latest
qwen2.5-coder:7b
qwen3:8b
```

- **Verification:** JSON response includes all four models.
- **⚠️ Caveats/Traps:** Ollama is intentionally bound to localhost.

**Step 4: Validate Qdrant**

- **Purpose:** Confirm vector database is protected and reachable.
- **Command(s):**

```bash
source /srv/ai/compose/core/.env
curl -fsS -H "api-key: ${QDRANT_API_KEY}" http://127.0.0.1:6333/collections
```

- **Explanation:** The unauthenticated request returned HTTP 401 in validation, which is expected with API key protection.
- **Expected Output:**

```text
{"result":{"collections":[...]}, "status":"ok", ...}
```

- **Verification:** Authenticated request returns collection data or an empty collection list.
- **⚠️ Caveats/Traps:** Do not remove `QDRANT__SERVICE__API_KEY` to make smoke tests easier.

**Step 5: Validate Speaches / Whisper**

- **Purpose:** Confirm local speech-to-text service is available for file, streaming, and realtime transcription clients.
- **Command(s):**

```bash
source /srv/ai/compose/core/.env
curl -fsS -H "Authorization: Bearer ${SPEACHES_API_KEY}" http://127.0.0.1:8000/health
curl -fsS -H "Authorization: Bearer ${SPEACHES_API_KEY}" http://127.0.0.1:8000/v1/models
```

- **Expected Output:**

```text
Health endpoint succeeds and models endpoint returns JSON.
```

- **Verification:** `SPEACHES_MODEL` is present in `/v1/models` and `/srv/ai/models/huggingface` is not empty.
- **⚠️ Caveats/Traps:** Keep the service bound to localhost because medical audio/transcripts are sensitive.

**Step 6: Validate loopback-only service exposure**

- **Purpose:** Preserve local-only security posture.
- **Command(s):**

```bash
ss -tlnp
```

- **Expected Output:**

```text
127.0.0.1:11434
127.0.0.1:8888
127.0.0.1:3000
127.0.0.1:6333
127.0.0.1:6334
127.0.0.1:7474
127.0.0.1:7687
127.0.0.1:8000
0.0.0.0:22
```

- **Verification:** AI services bind to `127.0.0.1`; only SSH binds broadly.
- **⚠️ Caveats/Traps:** Do not bind Ollama, Speaches, Qdrant, Neo4j, or Jupyter to `0.0.0.0` without an explicit reverse-proxy/auth policy.

### 3. Configuration Files

Validation script:

```bash
scripts/validate_stack.sh
```

The script uses `sudo docker` fallback, Qdrant API-key-aware checks, Speaches bearer auth when configured, and model-storage checks for `/srv/ai/ollama` plus `/srv/ai/models/huggingface`.

### 4. Troubleshooting & Recovery

- Plain `docker` permission denied: use `sudo docker` or run the updated scripts.
- Qdrant 401: include `-H "api-key: ${QDRANT_API_KEY}"`.
- Speaches 401: include `-H "Authorization: Bearer ${SPEACHES_API_KEY}"`.
- Ollama no models: run `sudo docker exec -it ollama ollama list`.
- Service missing from `ss`: inspect `sudo docker compose ps` and service logs.
