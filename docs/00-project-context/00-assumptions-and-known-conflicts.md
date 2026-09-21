# Assumptions and Known Conflicts

### 1. Objective & Prerequisites

- Declare the validated baseline and remaining documentation assumptions.
- Required previous state: host and VM state scripts have been run.
- Estimated time: 5 minutes. Risk level: low.

### 2. Resolved Conflicts

**Step 1: Ubuntu version**

- **Purpose:** Remove the prior 24.04/26.04 ambiguity.
- **Command(s):**

```bash
cat /etc/os-release
```

- **Expected Output:**

```text
PRETTY_NAME="Ubuntu 26.04 LTS"
VERSION="26.04 LTS (Resolute Raccoon)"
```

- **Verification:** This repository now documents Ubuntu Server 26.04 LTS as the working guest OS.
- **⚠️ Caveats/Traps:** Earlier 24.04 references are historical notes unless explicitly marked as alternate guidance.

**Step 2: Current status**

- **Purpose:** Replace stale roadmap assumptions with measured state.
- **Command(s):**

```bash
VMID=2020 scripts/gather_host_state.sh
scripts/gather_vm_state.sh
```

- **Expected Output:**

```text
Proxmox VE 9.1.0
Ubuntu 26.04 LTS
RTX 5060 Ti visible in VM
NVIDIA-SMI 595.71.05
/srv/ai mounted on /dev/sdb1
Ollama models listed by API
```

- **Verification:** See [Validated State](03-validated-state-2026-05-21.md).
- **⚠️ Caveats/Traps:** The old future roadmap is archived and must not be treated as current deployment state.

### 3. Configuration Files

The canonical validated files are under:

```text
configs/
scripts/
archive/validation/
```

### 4. Known Open Items

- Docker commands require root access; keep the user out of the Docker group by default and use the root-owned maintenance wrappers from the remediation plan for noninteractive validation.
- Qdrant is API-key protected; unauthenticated health checks may return HTTP 401.
- Speaches may require `Authorization: Bearer ${SPEACHES_API_KEY}` even for health/model validation; scripts now include the header when a key is configured.
- Root was measured at 83% on 2026-06-03. Ollama models were verified under `/srv/ai/ollama`; root cleanup should focus first on `/swap.img`, duplicate `/swapfile` entries, and a sudo-level disk audit.
- RAG ingestion, reranking, graph constraints, Zotero export, and agent policy/audit setup are tracked in the remediation plan.
- Proxmox package report says `pve-edk2-firmware: not correctly installed`; the current VM boots, but this should be reviewed during maintenance.
