# GPU Not Visible in VM

## 1. Objective & Prerequisites

- Provide focused recovery steps for a known failure mode.
- Required previous state: access to either Proxmox host shell or Ubuntu VM shell, as specified.
- Estimated time: variable. Risk level: medium to high.

## 2. Step-by-Step Execution

### Step 1: Check inside Ubuntu

- **Purpose:** Confirm whether the VM sees the PCI device.
- **Command(s):**

```bash
lspci -nn | grep -Ei 'nvidia|10de|vga|3d|display|audio'
```

- **Explanation:** If this returns nothing, the issue is passthrough/device assignment, not drivers.
- **Expected Output:**

```text
... NVIDIA Corporation ...
```

- **Verification:** `lspci -nnk -d 10de:` -> NVIDIA device present.
- **⚠️ Caveats/Traps:** Do not install/reinstall drivers until the PCI device is visible.

### Step 2: Check Proxmox binding and VM config

- **Purpose:** Verify host VFIO and VM hostpci settings.
- **Command(s):**

```bash
lspci -nnk -d 10de:
qm config ${VMID} | grep -E 'hostpci|machine|bios'
```

- **Explanation:** Host should show `vfio-pci`; VM should have `hostpci0`.
- **Expected Output:**

```text
Kernel driver in use: vfio-pci
hostpci0: ...
```

- **Verification:** Both expected outputs appear.
- **⚠️ Caveats/Traps:** VM must be stopped and started after PCI config changes.

## 3. Configuration Files

- `/etc/modprobe.d/vfio.conf`
- `/etc/modules-load.d/vfio.conf`
- `/etc/pve/qemu-server/${VMID}.conf`

## 4. Troubleshooting & Recovery

- If host uses nouveau, fix blacklist and initramfs.
- If no `hostpci0`, add the GPU to VM hardware.
- If VM fails to start, remove passthrough and re-add with correct PCIe settings.
