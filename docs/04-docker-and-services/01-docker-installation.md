# Docker Installation

### 1. Objective & Prerequisites

- Install Docker Engine and configure its data root on `/srv/ai/docker`.
- Required previous state: `/srv/ai` mounted on large AI disk.
- Estimated time: 20 minutes. Risk level: medium.

### 2. Step-by-Step Execution

**Step 1: Configure Docker data-root before heavy use**

- **Purpose:** Prevent Docker images, layers, and build cache from filling `/`.
- **Command(s):**

```bash
sudo mkdir -p /etc/docker /srv/ai/docker
sudo cp configs/ubuntu-vm/docker-daemon.json /etc/docker/daemon.json
python3 -m json.tool /etc/docker/daemon.json
```

- **Explanation:** `data-root` must be `/srv/ai/docker` before model and image pulls.
- **Expected Output:**

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

- **Verification:** JSON validation succeeds.
- **⚠️ Caveats/Traps:** If Docker is already installed, stop Docker before migrating `/var/lib/docker`.

**Step 2: Install Docker packages**

- **Purpose:** Install Docker Engine, CLI, Buildx, and Compose plugin.
- **Command(s):**

```bash
sudo apt update
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null <<'EOF'
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME}
Components: stable
Architectures: amd64
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

- **Explanation:** `${UBUNTU_CODENAME}` must match `/etc/os-release`; do not assume a codename from another release.
- **Expected Output:**

```text
Setting up docker-ce ...
Setting up docker-compose-plugin ...
```

- **Verification:** `sudo docker info | grep 'Docker Root Dir'` -> `/srv/ai/docker`.
- **⚠️ Caveats/Traps:** If Docker's repository does not yet support Ubuntu 26.04 codename, use the officially supported fallback only after validating compatibility.

### 3. Configuration Files

`/etc/docker/daemon.json` from `configs/ubuntu-vm/docker-daemon.json`. It should include both `/srv/ai/docker` as the data root and the NVIDIA container runtime entry.

### 4. Troubleshooting & Recovery

- If Docker root shows `/var/lib/docker`, stop Docker and migrate or reconfigure before pulling images.
- If `docker.sources` fails, check `${UBUNTU_CODENAME}`.
- If disk fills during build, run `sudo docker system df` and prune only after confirming no important containers are needed.
