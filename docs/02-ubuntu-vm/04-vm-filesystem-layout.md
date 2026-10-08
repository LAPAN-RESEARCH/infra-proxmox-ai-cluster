# VM Filesystem Layout

## 1. Objective & Prerequisites

- Ensure the Ubuntu VM separates OS data from AI service data.
- Required previous state: VM online; second disk attached as `sdb`.
- Estimated time: 10-30 minutes. Risk level: medium if editing `/etc/fstab`.

## 2. Step-by-Step Execution

### Step 1: Verify root and AI data mounts

- **Purpose:** Confirm that `/srv/ai` is a real mounted filesystem, not a directory inside `/`.
- **Command(s):**

```bash
df -h / /srv/ai
findmnt /srv/ai
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
```

- **Explanation:** The OS disk should hold `/`; the 500G disk should hold `/srv/ai`.
- **Expected Output:**

```text
/dev/mapper/ubuntu--vg-ubuntu--lv   96G   65G   27G  72% /
/dev/sdb1                          492G   12G  480G   3% /srv/ai

TARGET  SOURCE    FSTYPE OPTIONS
/srv/ai /dev/sdb1 ext4   rw,noatime
```

- **Verification:** `/srv/ai` source is `/dev/sdb1`.
- **⚠️ Caveats/Traps:** If `findmnt /srv/ai` returns nothing, stop Docker before pulling or building anything.

### Step 2: Keep Docker storage under `/srv/ai`

- **Purpose:** Prevent Docker image layers and build cache from filling `/`.
- **Command(s):**

```bash
sudo cat /etc/docker/daemon.json
sudo docker info | grep 'Docker Root Dir'
```

- **Explanation:** Docker's `data-root` should point to the AI data disk.
- **Expected Output:**

```text
Docker Root Dir: /srv/ai/docker
```

- **Verification:** `Docker Root Dir` is not `/var/lib/docker`.
- **⚠️ Caveats/Traps:** If Docker still uses `/var/lib/docker`, stop Docker and migrate before downloading models.

### Step 3: Review swap

- **Purpose:** Avoid accidental swap duplication or root consumption.
- **Command(s):**

```bash
swapon --show
free -h
```

- **Explanation:** The validated VM currently has two swap files.
- **Expected Output:**

```text
/swap.img   file   8G
/swapfile   file  16G
Swap:       23Gi
```

- **Verification:** Swap exists and is unused under normal operation.
- **⚠️ Caveats/Traps:** Two swap files are not immediately dangerous, but simplify to one later for clarity.

## 3. Configuration Files

`/etc/fstab` should include `/srv/ai` by UUID:

```text
UUID=${AI_DATA_UUID} /srv/ai ext4 defaults,noatime 0 2
```

Docker daemon config:

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

- If `/` fills, check `/var/lib/docker`, `/srv/ai` mount state, `/var/tmp`, and journal logs.
- If `/srv/ai` is missing after boot, run `sudo mount -a` and inspect `/etc/fstab`.
- If Docker starts before `/srv/ai` mounts, stop Docker, mount `/srv/ai`, then restart Docker.
- If root remains above 80%, inspect `sudo du -xhd1 / | sort -h`.
