# Guest NVIDIA Driver

### 1. Objective & Prerequisites

- Install and validate the NVIDIA driver inside the Ubuntu VM.
- Required previous state: GPU visible inside Ubuntu with `lspci`; host uses VFIO.
- Estimated time: 15-30 minutes. Risk level: medium.

### 2. Step-by-Step Execution

**Step 1: Confirm PCI device visibility**

- **Purpose:** Verify passthrough before installing or debugging drivers.
- **Command(s):**

```bash
lspci -nn | grep -Ei 'nvidia|10de|vga|3d|display|audio'
```

- **Explanation:** Drivers cannot fix a missing PCI device.
- **Expected Output:**

```text
01:00.0 VGA compatible controller [0300]: NVIDIA Corporation GB206 [GeForce RTX 5060 Ti] [10de:2d04]
01:00.1 Audio device [0403]: NVIDIA Corporation GB206 High Definition Audio Controller [10de:22eb]
```

- **Verification:** Both GPU and audio functions are visible.
- **⚠️ Caveats/Traps:** Do not reinstall NVIDIA packages if `lspci` does not show NVIDIA; fix Proxmox passthrough first.

**Step 2: Install server driver branch**

- **Purpose:** Provide compute-capable NVIDIA userspace and kernel modules.
- **Command(s):**

```bash
sudo apt update
sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers install --gpgpu
sudo apt install -y nvidia-utils-595-server
sudo reboot
```

- **Explanation:** The validated VM uses the `595-server` branch.
- **Expected Output:**

```text
nvidia-utils-595-server ...
```

- **Verification:** `dpkg -l | grep -E 'nvidia-utils|libnvidia'` shows `595-server` packages.
- **⚠️ Caveats/Traps:** Match `nvidia-utils-*` to the installed driver branch.

**Step 3: Validate driver**

- **Purpose:** Confirm the guest owns the GPU and CUDA runtime can see it.
- **Command(s):**

```bash
nvidia-smi
```

- **Expected Output:**

```text
NVIDIA-SMI 595.71.05
Driver Version: 595.71.05
CUDA Version: 13.2
NVIDIA GeForce RTX 5060 Ti
Memory-Usage ... / 16311MiB
```

- **Verification:** `nvidia-smi` succeeds and reports the RTX 5060 Ti.
- **⚠️ Caveats/Traps:** If `nvidia-smi` is missing, install the matching `nvidia-utils-*-server` package.

### 3. Configuration Files

No guest config file is required for basic driver operation. NVIDIA driver packages are managed by APT.

### 4. Troubleshooting & Recovery

- Missing command: `sudo apt install -y nvidia-utils-595-server`.
- Driver mismatch: purge old non-server packages and reinstall the server branch.
- Secure Boot/MOK errors: check `mokutil --sb-state` and DKMS logs.
- GPU missing: return to [GPU Not Visible in VM](../07-troubleshooting/03-gpu-not-visible-in-vm.md).
