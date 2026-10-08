# Updates and Rollbacks

## 1. Objective & Prerequisites

- Update host, VM, Docker images, and drivers safely.
- Required previous state: working backup exists.
- Estimated time: 30-120 minutes. Risk level: high for GPU/driver updates.

## 2. Step-by-Step Execution

### Step 1: Snapshot or backup before updates

- **Purpose:** Ensure recovery if Docker or NVIDIA updates break the stack.
- **Command(s):**

```bash
scripts/backup_ai_stack.sh
VMID=${VMID} scripts/gather_host_state.sh
scripts/gather_vm_state.sh
```

- **Explanation:** Backups plus state logs provide rollback context.
- **Expected Output:**

```text
Wrote ...tar.gz
Wrote host-state-...
Wrote vm-state-...
```

- **Verification:** Backup archive and state files exist.
- **⚠️ Caveats/Traps:** Do not update NVIDIA drivers and Docker images in the same maintenance window unless necessary.

### Step 2: Update Compose images

- **Purpose:** Refresh AI services while preserving data volumes.
- **Command(s):**

```bash
cd /srv/ai/compose/core
sudo docker compose pull
sudo docker compose build --pull
sudo docker compose up -d
scripts/validate_stack.sh
```

- **Explanation:** Compose recreates containers against existing bind-mounted data directories.
- **Expected Output:**

```text
Container ... Started
```

- **Verification:** `scripts/validate_stack.sh` -> All checks pass.
- **⚠️ Caveats/Traps:** Pin tags or digests for reproducibility after validation.

## 3. Configuration Files

- `/srv/ai/compose/core/docker-compose.yml`
- `/srv/ai/compose/core/.env`

## 4. Troubleshooting & Recovery

- Roll back image tag in `.env`, then run `sudo docker compose up -d`.
- Restore service data from backup only with containers stopped.
- Remove GPU passthrough temporarily with `qm set ${VMID} -delete hostpci0`.
