# Validated State — 2026-05-21

### 1. Objective & Prerequisites

- Capture the verified post-recovery state from `scripts/gather_host_state.sh` and `scripts/gather_vm_state.sh`.
- Required previous state: Proxmox host reachable over SSH; Ubuntu AI VM online.
- Estimated time: read-only reference. Risk level: low.

### 2. Validated Proxmox Host State

**Step 1: Host platform**

- **Purpose:** Establish the exact host version used for this deployment.
- **Command(s):**

```bash
pveversion -v
uname -a
```

- **Expected Output:**

```text
proxmox-ve: 9.1.0
pve-manager: 9.1.16
Linux lapan 7.0.2-4-pve ...
```

- **Verification:** Proxmox VE 9.1.0 and kernel `7.0.2-4-pve` are present.
- **⚠️ Caveats/Traps:** Earlier notes mentioning kernel `7.0.2-2-pve` are outdated.

**Step 2: Host storage**

- **Purpose:** Confirm the previous `local` storage exhaustion was corrected.
- **Command(s):**

```bash
df -h /
pvesm status
lvs -a -o lv_name,vg_name,lv_size,lv_attr,origin,data_percent,metadata_percent,devices
```

- **Expected Output:**

```text
/dev/mapper/lapan--vg-root   62G  5.6G   54G  10% /

Name         Type     Status     Total       Used       Available     %
local        dir      active     64695968    5843908    55638640      9.03%
local-lvm    lvmthin  active     891289600   56775147   834514452     6.37%

data            lapan-vg 850.00g twi-aotz--  6.37  12.15
vm-2020-disk-0  lapan-vg 100.00g Vwi-aotz-- 42.09
vm-2020-disk-1  lapan-vg 500.00g Vwi-aotz--  2.41
```

- **Verification:** VM disks are no longer backed by root-filled `local`; they are on `local-lvm`.
- **⚠️ Caveats/Traps:** The EFI disk remains on `local`; this is small and acceptable.

**Step 3: IOMMU and VFIO**

- **Purpose:** Confirm the GPU is bound to VFIO on the host.
- **Command(s):**

```bash
journalctl -k | grep -Ei 'iommu|amd-vi|vfio'
lspci -nnk -d 10de:
```

- **Expected Output:**

```text
iommu: Default domain type: Passthrough
vfio_pci: add [10de:2d04...]
vfio_pci: add [10de:22eb...]

01:00.0 ... NVIDIA ... [10de:2d04]
    Kernel driver in use: vfio-pci
01:00.1 ... NVIDIA ... [10de:22eb]
    Kernel driver in use: vfio-pci
```

- **Verification:** Both GPU functions use `vfio-pci`.
- **⚠️ Caveats/Traps:** Do not install NVIDIA drivers on the Proxmox host.

**Step 4: VM configuration**

- **Purpose:** Confirm the VM is using the intended Proxmox hardware model.
- **Command(s):**

```bash
qm config 2020
```

- **Expected Output:**

```text
agent: 1
bios: ovmf
cores: 8
cpu: host
hostpci0: 0000:01:00,pcie=1
machine: q35
memory: 24576
scsi0: local-lvm:vm-2020-disk-0,iothread=1,size=100G
scsi1: local-lvm:vm-2020-disk-1,iothread=1,size=500G
```

- **Verification:** `cpu: host`, `q35`, `OVMF`, `hostpci0`, and `local-lvm` disks are present.
- **⚠️ Caveats/Traps:** If `cpu` reverts to `x86-64-v2-AES`, Polars and other scientific packages may lose AVX/AVX2/FMA.

### 3. Validated Ubuntu VM State

**Step 1: OS and kernel**

- **Purpose:** Record the final accepted guest OS.
- **Command(s):**

```bash
cat /etc/os-release
uname -a
```

- **Expected Output:**

```text
PRETTY_NAME="Ubuntu 26.04 LTS"
VERSION="26.04 LTS (Resolute Raccoon)"
Linux lapan-ai 7.0.0-15-generic ...
```

- **Verification:** Ubuntu 26.04 LTS is the working target.
- **⚠️ Caveats/Traps:** Any older Ubuntu 24.04 references are now historical.

**Step 2: CPU features**

- **Purpose:** Confirm the VM sees the real CPU feature set.
- **Command(s):**

```bash
grep -m1 '^flags' /proc/cpuinfo | grep -Eo '\b(avx2|avx|fma|bmi1|bmi2|abm|movbe|pclmulqdq)\b' | sort -u
```

- **Expected Output:**

```text
abm
avx
avx2
bmi1
bmi2
fma
movbe
pclmulqdq
```

- **Verification:** Polars imports without CPU feature warnings.
- **⚠️ Caveats/Traps:** Do not suppress Polars warnings with `POLARS_SKIP_CPU_CHECK`.

**Step 3: Guest storage**

- **Purpose:** Confirm `/srv/ai` is mounted to the 500 GB disk and root has space.
- **Command(s):**

```bash
df -h
findmnt /srv/ai
lsblk -o NAME,SIZE,FSTYPE,TYPE,MOUNTPOINTS
```

- **Expected Output:**

```text
/dev/mapper/ubuntu--vg-ubuntu--lv   96G   65G   27G  72% /
/dev/sdb1                          492G   12G  480G   3% /srv/ai

TARGET  SOURCE    FSTYPE OPTIONS
/srv/ai /dev/sdb1 ext4   rw,noatime
```

- **Verification:** `/srv/ai` is on `/dev/sdb1`, not a directory inside `/`.
- **⚠️ Caveats/Traps:** Root is already at 72%; keep Docker data-root on `/srv/ai/docker`.

**Step 4: Swap**

- **Purpose:** Record current swap and identify cleanup opportunity.
- **Command(s):**

```bash
swapon --show
free -h
```

- **Expected Output:**

```text
/swap.img   file   8G
/swapfile   file  16G
Swap:       23Gi
```

- **Verification:** Swap is functional.
- **⚠️ Caveats/Traps:** There are two swap files. This is not urgent, but the VM can later be simplified to one swap file.

**Step 5: NVIDIA driver**

- **Purpose:** Confirm the guest owns the GPU and has a working NVIDIA driver.
- **Command(s):**

```bash
lspci -nn | grep -Ei 'nvidia|10de'
nvidia-smi
```

- **Expected Output:**

```text
01:00.0 ... NVIDIA Corporation GB206 [GeForce RTX 5060 Ti] [10de:2d04]
01:00.1 ... NVIDIA Corporation GB206 High Definition Audio Controller [10de:22eb]

NVIDIA-SMI 595.71.05
Driver Version: 595.71.05
CUDA Version: 13.2
NVIDIA GeForce RTX 5060 Ti
Memory: 16311 MiB
```

- **Verification:** `nvidia-smi` works and shows Ollama using GPU memory.
- **⚠️ Caveats/Traps:** NVIDIA packages are the `595-server` branch; install matching `nvidia-utils-595-server` if `nvidia-smi` disappears.

**Step 6: AI services**

- **Purpose:** Confirm the service security posture.
- **Command(s):**

```bash
curl -fsS http://127.0.0.1:11434/api/tags
ss -tlnp
```

- **Expected Output:**

```text
Ollama models:
embeddinggemma:latest
bge-m3:latest
qwen2.5-coder:7b
qwen3:8b

Listening ports:
127.0.0.1:11434
127.0.0.1:8888
127.0.0.1:3000
127.0.0.1:6333
127.0.0.1:6334
127.0.0.1:7474
127.0.0.1:7687
0.0.0.0:22
```

- **Verification:** AI services bind to loopback only; SSH is the only broad listener.
- **⚠️ Caveats/Traps:** Qdrant returns HTTP 401 without the API key; that is expected when `QDRANT__SERVICE__API_KEY` is enabled.

### 3. Configuration Files

Raw validation logs are archived in:

```text
archive/validation/host-state-20260521-164641.txt
archive/validation/vm-state-20260521-194735.txt
```

### 4. Troubleshooting & Recovery

- If Docker commands fail with permission denied, run `sudo docker ...` or use the updated scripts that auto-fallback to `sudo`.
- If Qdrant smoke tests return `401`, provide the API key from `/srv/ai/compose/core/.env`.
- If root usage exceeds 80%, check Docker data-root and confirm `/srv/ai` is mounted before starting containers.
- If GPU disappears inside the VM, verify `hostpci0` in Proxmox and `vfio-pci` binding on the host.
