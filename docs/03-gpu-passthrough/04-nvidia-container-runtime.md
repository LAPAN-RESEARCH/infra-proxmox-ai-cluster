# NVIDIA Container Runtime

## 1. Objective & Prerequisites

- Allow Docker containers to access the passed-through RTX 5060 Ti.
- Required previous state: `nvidia-smi` works inside the VM.
- Estimated time: 10-20 minutes. Risk level: medium.

## 2. Step-by-Step Execution

### Step 1: Install NVIDIA Container Toolkit

- **Purpose:** Add Docker GPU runtime integration.
- **Command(s):**

```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey   | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list   | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g'   | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

- **Explanation:** `nvidia-ctk` updates Docker runtime configuration.
- **Expected Output:**

```text
nvidia-container-toolkit 1.19.0-1
```

- **Verification:** `dpkg -l | grep nvidia-container` shows toolkit packages.
- **⚠️ Caveats/Traps:** Restart Docker after runtime configuration.

### Step 2: Validate GPU from container

- **Purpose:** Confirm containers can use the GPU.
- **Command(s):**

```bash
sudo docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

- **Expected Output:**

```text
NVIDIA-SMI 595.71.05
NVIDIA GeForce RTX 5060 Ti
```

- **Verification:** The container reports the same GPU as the host guest driver.
- **⚠️ Caveats/Traps:** The CUDA image tag can lag the host-reported CUDA version; this test validates runtime visibility, not full CUDA toolkit development.

## 3. Configuration Files

Docker daemon config should remain:

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

- If Docker reports no GPU, rerun `sudo nvidia-ctk runtime configure --runtime=docker`.
- If Docker commands require root, use `sudo docker` or keep the current secure default.
- If container test fails but host `nvidia-smi` works, inspect `/etc/docker/daemon.json` and restart Docker.
