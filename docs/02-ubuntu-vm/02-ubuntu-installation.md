# Ubuntu Installation

## 1. Objective & Prerequisites

- Install Ubuntu Server 26.04 LTS minimally as the AI guest OS.
- Required previous state: VM created with q35, OVMF, VirtIO, and no GPU passthrough yet.
- Estimated time: 20-40 minutes. Risk level: low.

## 2. Step-by-Step Execution

### Step 1: Install minimal Ubuntu Server

- **Purpose:** Create a small, stable, headless base system.
- **Command(s):**

```bash
# Interactive installer choices:
# Minimal server installation
# Install OpenSSH server: yes
# Third-party drivers during install: no
# Desktop environment: no
```

- **Explanation:** NVIDIA drivers are installed later only after passthrough is confirmed.
- **Expected Output:**

```text
Installation complete. Reboot now.
```

- **Verification:** `cat /etc/os-release` -> Reports Ubuntu Server 26.04 LTS.
- **⚠️ Caveats/Traps:** Do not install desktop packages or NVIDIA drivers during the installer.

### Step 2: Install base tools

- **Purpose:** Add administration tools required for the rest of the deployment.
- **Command(s):**

```bash
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y qemu-guest-agent openssh-server curl ca-certificates gnupg git jq htop tmux unzip rsync build-essential python3 python3-venv python3-pip vim
```

- **Explanation:** These packages support SSH, guest-agent integration, package repository setup, editing, and diagnostics.
- **Expected Output:**

```text
Setting up qemu-guest-agent ...
Setting up openssh-server ...
...
```

- **Verification:** `systemctl status ssh --no-pager` -> SSH service is active.
- **⚠️ Caveats/Traps:** `qemu-guest-agent` may show `static` for enablement; active runtime status matters more.

## 3. Configuration Files

No static files are required in this phase.

## 4. Troubleshooting & Recovery

- If SSH is missing, install `openssh-server`.
- If guest agent does not work, enable QEMU Guest Agent in Proxmox VM Options and cold-start the VM.
- If copy/paste fails in noVNC, use SSH or xterm.js serial console instead.
