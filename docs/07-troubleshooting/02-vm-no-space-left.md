# VM: No Space Left on Device

## 1. Objective & Prerequisites

- Recover Ubuntu VM filesystem exhaustion caused by Docker, Ollama, or missing `/srv/ai` mount.
- Required previous state: console or SSH access to the VM, or recovery-mode boot.
- Estimated time: 10-60 minutes. Risk level: medium.

## 2. Step-by-Step Execution

### Step 1: Stop Docker

- **Purpose:** Prevent further writes while diagnosing space usage.
- **Command(s):**

```bash
sudo systemctl stop docker docker.socket containerd
```

- **Expected Output:**

```text
No output on success.
```

- **Verification:** `systemctl is-active docker` returns inactive.
- **⚠️ Caveats/Traps:** Do not prune before identifying whether data should be preserved.

### Step 2: Confirm mount layout

- **Purpose:** Verify `/srv/ai` is mounted on the 500G disk.
- **Command(s):**

```bash
df -h / /srv/ai
findmnt /srv/ai || true
sudo du -xhd1 / 2>/dev/null | sort -h
```

- **Expected Output in current validated state:**

```text
/        96G   65G   27G  72%
/srv/ai 492G   12G  480G   3%
/srv/ai /dev/sdb1 ext4 rw,noatime
```

- **Verification:** `/srv/ai` is mounted; root has free space.
- **⚠️ Caveats/Traps:** If `/srv/ai` is missing, Docker/Ollama may have written data into `/`.

### Step 3: Verify Docker data-root

- **Purpose:** Ensure Docker storage lives on the AI data disk.
- **Command(s):**

```bash
sudo docker info | grep 'Docker Root Dir'
```

- **Expected Output:**

```text
Docker Root Dir: /srv/ai/docker
```

- **Verification:** It must not be `/var/lib/docker`.
- **⚠️ Caveats/Traps:** Moving Docker data requires Docker to be stopped.

## 3. Configuration Files

Docker daemon:

```json
{
  "data-root": "/srv/ai/docker",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "args": []
    }
  }
}
```

## 4. Troubleshooting & Recovery

- If root is full, clean APT cache, journal logs, `/tmp`, and `/var/tmp`.
- If Docker root is wrong, stop Docker, migrate `/var/lib/docker` to `/srv/ai/docker`, and restart Docker.
- If `/srv/ai` does not mount, fix `/etc/fstab` and run `sudo mount -a`.
- If Ollama models are incomplete or corrupted, remove unused models through `ollama rm` after Docker is healthy.
