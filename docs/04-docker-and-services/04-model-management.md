# Model Management

## 1. Objective & Prerequisites

- Manage local Ollama models without exhausting host or guest storage.
- Required previous state: Ollama container running; `/srv/ai` mounted with sufficient free space.
- Estimated time: variable by model size. Risk level: medium due to disk growth.

## 2. Step-by-Step Execution

### Step 1: Check capacity before pulling

- **Purpose:** Avoid repeating the storage exhaustion incident.
- **Command(s):**

```bash
df -h / /srv/ai
sudo docker exec -it ollama ollama list
```

- **Explanation:** Ollama models are stored in the bind mount mapped to `/srv/ai/ollama`; inside the container `OLLAMA_MODELS=/root/.ollama/models`.
- **Expected Output:**

```text
/dev/sdb1  492G  12G  480G  3% /srv/ai
```

- **Verification:** Keep tens of GB free before pulling larger models.
- **⚠️ Caveats/Traps:** Model pulls grow the VM disk and consume Proxmox thin-pool space.

### Step 2: Maintain the validated starter model set

- **Purpose:** Cover coding, research, and embedding tasks with a small initial inventory.
- **Command(s):**

```bash
sudo docker exec -it ollama ollama list
```

- **Expected Output:**

```text
qwen3:8b
qwen2.5-coder:7b
bge-m3
embeddinggemma
```

- **Verification:** `curl http://127.0.0.1:11434/api/tags` returns the same inventory.
- **⚠️ Caveats/Traps:** Do not download many models before a backup and capacity review.

### Step 3: Confirm models are not on root

- **Purpose:** Catch accidental root-side caches before they grow.
- **Command(s):**

```bash
sudo du -sh /srv/ai/ollama /srv/ai/models/huggingface /home/*/.ollama /usr/share/ollama/.ollama /var/lib/ollama /var/lib/docker 2>/dev/null || true
sudo docker info | grep 'Docker Root Dir'
```

- **Expected Output:**

```text
/srv/ai/ollama
/srv/ai/models/huggingface
Docker Root Dir: /srv/ai/docker
```

- **Verification:** Large model caches are on `/srv/ai`, not `/`.
- **⚠️ Caveats/Traps:** Stop Docker before moving a model cache.

### Step 4: Pull additional models safely

- **Purpose:** Add models only after checking disk impact.
- **Command(s):**

```bash
df -h /srv/ai
sudo docker exec -it ollama ollama pull ${MODEL_NAME}
df -h /srv/ai
pvesm status   # run on Proxmox host
```

- **Explanation:** Check both the guest filesystem and Proxmox thin pool after large downloads.
- **Expected Output:**

```text
pulling manifest
success
```

- **Verification:** `ollama list` shows the new model.
- **⚠️ Caveats/Traps:** A guest with free `/srv/ai` can still fill a thin-provisioned host pool if unmanaged.

## 3. Configuration Files

Ollama data mount in Compose:

```yaml
volumes:
  - /srv/ai/ollama:/root/.ollama
```

## 4. Troubleshooting & Recovery

- Remove unused model: `sudo docker exec -it ollama ollama rm ${MODEL_NAME}`.
- Inspect model storage: `sudo du -sh /srv/ai/ollama`.
- If disk fills during pull, stop Ollama and remove incomplete model blobs only after identifying the directory.
- Always recheck `pvesm status` on the host after large model changes.
