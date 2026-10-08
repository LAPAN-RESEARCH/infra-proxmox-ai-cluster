# Backups and Restore

## 1. Objective & Prerequisites

- Define consistent backups for configuration, service data, and notebooks.
- Required previous state: AI stack running and `/srv/ai/backups` available.
- Estimated time: 10-60 minutes depending on data size. Risk level: medium.

## 2. Step-by-Step Execution

### Step 1: Run backup script

- **Purpose:** Capture critical service state before updates or major changes.
- **Command(s):**

```bash
scripts/backup_ai_stack.sh
```

- **Explanation:** The script backs up Compose files and selected service directories.
- **Expected Output:**

```text
Wrote /srv/ai/backups/ai-stack-${STAMP}.tar.gz
```

- **Verification:** `tar -tzf /srv/ai/backups/ai-stack-${STAMP}.tar.gz | head` -> Archive is readable.
- **⚠️ Caveats/Traps:** Large model files may be excluded unless explicitly added.

## 3. Configuration Files

Backup script:

```text
scripts/backup_ai_stack.sh
```

## 4. Troubleshooting & Recovery

- If backup fails due to permissions, run with sudo or adjust directory ownership.
- If backup fills disk, move backups off `/srv/ai` to external storage.
- Restore only with services stopped: `sudo docker compose down` before replacing volumes.
