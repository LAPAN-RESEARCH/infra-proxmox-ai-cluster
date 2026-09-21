# nvidia-smi Missing or Failing

### 1. Objective & Prerequisites

- Provide focused recovery steps for a known failure mode.
- Required previous state: access to either Proxmox host shell or Ubuntu VM shell, as specified.
- Estimated time: variable. Risk level: medium to high.

### 2. Step-by-Step Execution

**Step 1: Determine whether command is missing or driver is failing**

- **Purpose:** Separate package installation problems from kernel driver problems.
- **Command(s):**

```bash
command -v nvidia-smi || true
dpkg -l | grep -E 'nvidia-driver|nvidia-utils|libnvidia|nvidia-dkms' | sort
```

- **Explanation:** `nvidia-smi` is provided by `nvidia-utils-*` packages.
- **Expected Output:**

```text
/usr/bin/nvidia-smi
```

- **Verification:** If missing, install matching utils package.
- **⚠️ Caveats/Traps:** Match utils version to installed driver branch.

**Step 2: Install matching utils**

- **Purpose:** Provide the user-space NVIDIA management tool.
- **Command(s):**

```bash
sudo apt install -y nvidia-utils-${NVIDIA_DRIVER_BRANCH}-server
sudo reboot
```

- **Explanation:** Example branch: `580`. Use `-server` if the installed driver is server branch.
- **Expected Output:**

```text
Setting up nvidia-utils-${NVIDIA_DRIVER_BRANCH}-server ...
```

- **Verification:** `nvidia-smi` -> Shows GPU table.
- **⚠️ Caveats/Traps:** Do not install several branches at once.

### 3. Configuration Files

No static config file required.

### 4. Troubleshooting & Recovery

- If module is blocked, check `mokutil --sb-state`.
- If DKMS failed, check `dkms status` and kernel headers.
- If command exists but fails, inspect `dmesg | grep -i nvidia`.
