# Capacity Planning

### 1. Objective & Prerequisites

- Track storage, RAM, VRAM, and thin-pool usage for the local AI stack.
- Required previous state: host and VM validation scripts available.
- Estimated time: 10 minutes per review. Risk level: low.

### 2. Step-by-Step Execution

**Step 1: Monitor Proxmox host storage**

- **Purpose:** Prevent recurrence of host root exhaustion.
- **Command(s):**

```bash
df -h /
pvesm status
lvs -a -o lv_name,lv_size,lv_attr,data_percent,metadata_percent
```

- **Expected Output:**

```text
/           62G  5.6G  54G  10%
local-lvm   891289600 KiB total, 6.37% used
data        850.00g twi-aotz-- 6.37 12.15
```

- **Verification:** Keep root below 80%; keep thin-pool data and metadata below 80%.
- **⚠️ Caveats/Traps:** Thin-provisioned disks can overcommit storage; monitor both guest and host.

**Step 2: Monitor Ubuntu VM storage**

- **Purpose:** Ensure root and AI data disk remain healthy.
- **Command(s):**

```bash
df -h / /srv/ai
sudo docker system df
sudo du -sh /srv/ai/ollama /srv/ai/docker /srv/ai/qdrant /srv/ai/neo4j /srv/ai/models 2>/dev/null
```

- **Expected Output:**

```text
/        96G   65G   27G  72%
/srv/ai 492G   12G  480G   3%
```

- **Verification:** Root should not exceed 80%; `/srv/ai` has large headroom.
- **⚠️ Caveats/Traps:** Docker build cache, model pulls, and duplicate swap files are the largest growth points. On 2026-06-03, Ollama was verified under `/srv/ai/ollama`; root pressure came from swap and privileged paths needing a sudo audit.

**Step 3: Monitor GPU memory**

- **Purpose:** Match models to available VRAM.
- **Command(s):**

```bash
nvidia-smi
```

- **Expected Output:**

```text
NVIDIA GeForce RTX 5060 Ti
834MiB / 16311MiB
/usr/bin/ollama
```

- **Verification:** Confirm workloads fit within 16 GB VRAM.
- **⚠️ Caveats/Traps:** Concurrent models in Ollama can keep memory allocated; tune `OLLAMA_KEEP_ALIVE` if needed.

### 3. Configuration Files

No file modification is required for monitoring.

### 4. Troubleshooting & Recovery

- If Proxmox `local-lvm` grows unexpectedly, check VM writes under `/srv/ai`.
- If VM `/` grows, check swap files, Docker root, `/var/log`, `/tmp`, and `/var/tmp`.
- If `/srv/ai` grows, check Ollama models, Speaches/Hugging Face model cache, and Qdrant/Neo4j data.
- If VRAM stays allocated, restart Ollama or reduce keep-alive.
