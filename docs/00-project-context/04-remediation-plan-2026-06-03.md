# Remediation Plan - 2026-06-03

## 1. Objective & Current Disk Finding

- Close every high and medium priority issue found in the 2026-06-03 review.
- Required previous state: Ubuntu VM online, `/srv/ai` mounted, Docker stack present.
- Estimated time: 2-4 hours plus model download and Zotero export time. Risk level: medium.

Disk check from the VM:

```text
/        96G   76G   16G  83%
/srv/ai 492G   12G  480G   3%
/srv/ai/ollama 11G
/srv/ai/models 8.0K
/swap.img 8.0G active
/swapfile 16G active
```

Conclusion: Ollama is not currently storing the installed model set on the root filesystem. The tracked Compose file bind-mounts `/srv/ai/ollama` to `/root/.ollama`, and the observed models live under `/srv/ai/ollama/models`. Root pressure is primarily from duplicated swap and other root-owned data that needs a sudo-level audit.

Run repo-relative `scripts/...` commands from `/home/hugo/proxmox-lapan-ai-setup`.

## 2. Infrastructure Remediation Sequence

### Step 1: Deploy tracked config and create the platform directories

- **Purpose:** Make the live Compose stack match the repo before recreating containers.
- **Command(s):**

```bash
scripts/deploy_ai_stack.sh
```

- **Verification:** `/srv/ai/compose/core/docker-compose.yml` includes explicit GPU requests, `/srv/ai/ollama` and `/srv/ai/models/huggingface` are the model caches, and `/srv/ai/agents` plus `/srv/ai/rag/{benchmarks,configs,pipelines,rerankers}` exist.

### Step 2: Fix Docker GPU access for containers

- **Purpose:** Make Ollama and Speaches use the RTX 5060 Ti from containers.
- **Command(s):**

```bash
sudo cp configs/ubuntu-vm/docker-daemon.json /etc/docker/daemon.json
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
sudo docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi

cd /srv/ai/compose/core
sudo docker compose --env-file .env up -d --force-recreate ollama speaches
```

- **Verification:** The CUDA container shows the GPU, `nvidia-smi` shows container GPU activity during an Ollama generation, and Ollama no longer reports `size_vram: 0` for `qwen3:8b`.

### Step 3: Keep all model downloads off root

- **Purpose:** Prevent future Ollama, Speaches, and reranker downloads from filling `/`.
- **Command(s):**

```bash
df -h / /srv/ai
sudo du -sh /srv/ai/ollama /srv/ai/models/huggingface /home/*/.ollama /usr/share/ollama/.ollama /var/lib/ollama /var/lib/docker 2>/dev/null || true
sudo docker exec ollama ollama list
```

- **Verification:** Ollama models are under `/srv/ai/ollama/models`; Hugging Face/Speaches/reranker files are under `/srv/ai/models/huggingface`; Docker root is `/srv/ai/docker`.
- **Recovery:** If a root-side Ollama cache exists, stop Ollama, copy it into `/srv/ai/ollama` with ownership preserved, recreate the container, verify `ollama list`, then remove only the verified duplicate root cache.

### Step 4: Fix Speaches model readiness

- **Purpose:** Ensure transcription is ready before live use.
- **Command(s):**

```bash
scripts/install_whisper_service.sh
source /srv/ai/compose/core/.env
curl -fsS -H "Authorization: Bearer ${SPEACHES_API_KEY}" http://127.0.0.1:8000/v1/models
du -sh /srv/ai/models/huggingface
```

- **Verification:** `/v1/models` lists `${SPEACHES_MODEL}` and `/srv/ai/models/huggingface` is no longer empty.

### Step 5: Reduce root filesystem usage

- **Purpose:** Bring `/` below the documented 80% threshold.
- **Command(s):**

```bash
swapon --show
sudo cp /etc/fstab /etc/fstab.$(date -u +%Y%m%d-%H%M%S).bak
sudo swapoff /swap.img
sudo sed -i '\#/swap.img#d' /etc/fstab
sudo awk '!seen[$0]++' /etc/fstab | sudo tee /etc/fstab.dedup >/dev/null
sudo mv /etc/fstab.dedup /etc/fstab
sudo rm /swap.img
sudo swapon --all
df -h /
swapon --show
```

- **Verification:** Only `/swapfile` remains active, `/etc/fstab` has one `/swapfile` entry, and `/` is below 80%.

### Step 6: Fix noninteractive maintenance access without adding Docker group

- **Purpose:** Allow validation/backup automation while keeping the `docker` group disabled by default.
- **Command(s):**

```bash
sudo install -o root -g root -m 0755 scripts/validate_stack.sh /usr/local/sbin/lapan-ai-validate
sudo install -o root -g root -m 0755 scripts/gather_vm_state.sh /usr/local/sbin/lapan-ai-gather-vm-state
sudo install -o root -g root -m 0755 scripts/backup_ai_stack.sh /usr/local/sbin/lapan-ai-backup
printf '%s\n' \
  'hugo ALL=(root) NOPASSWD: /usr/local/sbin/lapan-ai-validate, /usr/local/sbin/lapan-ai-gather-vm-state, /usr/local/sbin/lapan-ai-backup' \
  | sudo tee /etc/sudoers.d/lapan-ai-maintenance >/dev/null
sudo chmod 0440 /etc/sudoers.d/lapan-ai-maintenance
sudo visudo -cf /etc/sudoers.d/lapan-ai-maintenance
```

- **Verification:** `sudo -n /usr/local/sbin/lapan-ai-validate` runs without prompting. Do not grant NOPASSWD to scripts in the user-writable repo path.

### Step 7: Create the first backup

- **Purpose:** Capture the corrected base state.
- **Command(s):**

```bash
sudo -n /usr/local/sbin/lapan-ai-backup
tar -tzf /srv/ai/backups/ai-stack-*.tar.gz | head
```

- **Verification:** `/srv/ai/backups` contains a readable archive with redacted env data, service state, RAG state, Zotero exports, and agent policy/audit state.

## 3. Research Platform Completion

### Step 1: Create the Qdrant collection

- **Command(s):**

```bash
source /srv/ai/compose/core/.env
curl -fsS -X PUT \
  -H "api-key: ${QDRANT_API_KEY}" \
  -H "Content-Type: application/json" \
  http://127.0.0.1:6333/collections/${RAG_COLLECTION:-research_chunks_bge_m3} \
  -d '{"vectors":{"size":1024,"distance":"Cosine"},"on_disk_payload":true}'
```

- **Verification:** Authenticated `GET /collections` lists `research_chunks_bge_m3`.

### Step 2: Apply Neo4j graph constraints

- **Command(s):**

```bash
source /srv/ai/compose/core/.env
neo4j_password="${NEO4J_AUTH#neo4j/}"
sudo docker exec neo4j cypher-shell -u neo4j -p "${neo4j_password}" "
CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.doc_id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;
CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE;
SHOW CONSTRAINTS;
"
```

- **Verification:** `SHOW CONSTRAINTS` lists the three constraints.

### Step 3: Add Zotero export

- **Command(s):**

```bash
mkdir -p /srv/ai/zotero/exports /srv/ai/zotero/pdfs
ls -lh /srv/ai/zotero/exports/library.bib
```

- **Verification:** Better BibTeX or equivalent export exists at `/srv/ai/zotero/exports/library.bib`; PDFs are linked or mirrored under `/srv/ai/zotero/pdfs`.

### Step 4: Implement RAG ingestion and reranking

- **Purpose:** Move from empty infrastructure to a usable research retrieval pipeline.
- **Implementation:** Use Jupyter or scripts under `/srv/ai/rag/pipelines` to parse Zotero PDFs into `/srv/ai/ingest/parsed`, chunk into `/srv/ai/ingest/chunks`, embed chunks with Ollama `bge-m3`, store vectors in Qdrant, and rerank BM25+dense candidates with `${RERANKER_MODEL:-BAAI/bge-reranker-v2-m3}` cached under `/srv/ai/models/huggingface`.
- **Verification:** A benchmark under `/srv/ai/rag/benchmarks` contains known questions, expected citations, baseline retrieval results, and reranked results.

### Step 5: Implement local agents with policies and audit

- **Purpose:** Allow constrained automation without broad shell or data access.
- **Implementation:** Use `/srv/ai/agents/{coding,papers,graphs,clinical,scratch}` for workspaces, `/srv/ai/agents/policies` for allowlists, and `/srv/ai/agents/audit` for append-only tool-call logs. Deny Docker socket mounts and unrestricted shell for research/clinical agents.
- **Verification:** Every agent tool call produces an audit entry, and agents cannot write outside their workspace.

## 4. Final Acceptance

- `df -h / /srv/ai` shows `/` below 80% and `/srv/ai` mounted.
- `sudo -n /usr/local/sbin/lapan-ai-validate` passes.
- `nvidia-smi` shows GPU use during Ollama and Speaches workloads.
- Speaches `/v1/models` lists the configured Whisper model.
- Qdrant has `research_chunks_bge_m3`; Neo4j has constraints; Zotero export exists.
- RAG benchmark returns cited chunks after reranking.
- Agent workspaces, policies, and audit logs exist and are included in backups.
