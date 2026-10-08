# Security Model

## 1. Objective & Prerequisites

- Defines the default security posture for a local-only AI research platform.
- Required previous state: network subnet and VM IP known.
- Estimated time: 20 minutes. Risk level: medium if firewall or SSH is misconfigured.

## 2. Step-by-Step Execution

### Step 1: Bind services to localhost

- **Purpose:** Prevent accidental LAN or public exposure of LLM, vector DB, graph DB, and notebook services.
- **Command(s):**

```bash
cd /srv/ai/compose/core
grep -n '127.0.0.1' docker-compose.yml
```

- **Explanation:** Compose port mappings should publish services to `127.0.0.1` unless a reverse proxy and authentication policy exists.
- **Expected Output:**

```text
127.0.0.1:11434:11434
127.0.0.1:3000:8080
127.0.0.1:6333:6333
127.0.0.1:7474:7474
127.0.0.1:8888:8888
```

- **Verification:** `ss -tlnp` -> Service listeners should be bound to `127.0.0.1` or the Docker bridge, not `0.0.0.0`.
- **⚠️ Caveats/Traps:** Docker-published ports may bypass simplistic firewall assumptions; bind explicitly to localhost.

### Step 2: Use SSH tunnels for access

- **Purpose:** Access UIs securely without exposing service ports directly.
- **Command(s):**

```bash
ssh   -L 3000:127.0.0.1:3000   -L 8888:127.0.0.1:8888   -L 7474:127.0.0.1:7474   -L 7687:127.0.0.1:7687   -L 6333:127.0.0.1:6333   -L 8000:127.0.0.1:8000   -L 11434:127.0.0.1:11434   ${VM_USER}@${VM_IP}
```

- **Explanation:** This maps local workstation ports to VM-local service ports through SSH.
- **Expected Output:**

```text
Last login: ...
${VM_USER}@${VM_HOSTNAME}:~$
```

- **Verification:** Open `http://127.0.0.1:3000` from the workstation while the tunnel is active.
- **⚠️ Caveats/Traps:** Do not expose clinical or private document services over unauthenticated LAN ports.

## 3. Configuration Files

Use `.env.example` as the pattern for secrets. Real `.env` files must not be committed.

Permissions:

```bash
chmod 600 /srv/ai/compose/core/.env
chmod 700 /srv/ai/secrets
```

## 4. Troubleshooting & Recovery

- If a service listens on `0.0.0.0`, edit `docker-compose.yml` and change the port mapping to `127.0.0.1:${HOST_PORT}:${CONTAINER_PORT}`.
- If SSH key login fails, re-enable console access before disabling passwords.
- If a notebook token leaks, rotate `JUPYTER_TOKEN` and restart Jupyter.
- If Qdrant API key leaks, rotate `QDRANT_API_KEY` and restart Qdrant.
- If a Speaches API key leaks, rotate `SPEACHES_API_KEY` and restart Speaches.
