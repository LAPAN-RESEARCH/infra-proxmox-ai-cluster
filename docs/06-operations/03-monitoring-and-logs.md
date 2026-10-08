# Monitoring and Logs

## 1. Objective & Prerequisites

- Monitor host, VM, GPU, Docker, and services.
- Required previous state: services running.
- Estimated time: 10 minutes. Risk level: low.

## 2. Step-by-Step Execution

### Step 1: Check capacity and GPU

- **Purpose:** Catch storage and GPU failures before workloads fail.
- **Command(s):**

```bash
df -h
free -h
nvidia-smi
sudo docker system df
```

- **Explanation:** These commands reveal disk, memory, GPU, and Docker usage.
- **Expected Output:**

```text
Filesystem ...
NVIDIA-SMI ...
TYPE            TOTAL     ACTIVE    SIZE
```

- **Verification:** `/`, `/srv/ai`, and Docker usage have safe free space.
- **⚠️ Caveats/Traps:** Model pulls can consume storage quickly.

### Step 2: Inspect service logs

- **Purpose:** Diagnose failed or restarting containers.
- **Command(s):**

```bash
cd /srv/ai/compose/core
sudo docker compose ps
sudo docker compose logs --tail=100 ollama
sudo docker compose logs --tail=100 open-webui
sudo docker compose logs --tail=100 qdrant
sudo docker compose logs --tail=100 neo4j
sudo docker compose logs --tail=100 jupyter
sudo docker compose logs --tail=100 speaches
```

- **Explanation:** Tail recent logs by service to avoid huge output.
- **Expected Output:**

```text
No repeated restart loops, permission errors, model download failures, or GPU runtime errors.
```

- **Verification:** No repeated crash loops or permission errors.
- **⚠️ Caveats/Traps:** Do not paste secrets from logs into public issues.

## 3. Configuration Files

Docker log rotation in `/etc/docker/daemon.json` prevents unbounded container logs.

## 4. Troubleshooting & Recovery

- If logs are too large, verify Docker log options and recreate containers.
- If GPU memory stays allocated, stop the relevant model container; Ollama and Speaches can both use VRAM.
- If Neo4j memory pressure occurs, lower heap/pagecache in Compose.
