# Add GPU to VM

### 1. Objective & Prerequisites

- Attach the VFIO-bound RTX GPU to the Ubuntu VM as a PCIe device.
- Required previous state: GPU functions bound to `vfio-pci`; Ubuntu VM boots and SSH works without GPU.
- Estimated time: 10 minutes. Risk level: medium.

### 2. Step-by-Step Execution

**Step 1: Stop the VM**

- **Purpose:** PCI hardware changes require the VM to be stopped.
- **Command(s):**

```bash
qm shutdown ${VMID}
qm status ${VMID}
```

- **Explanation:** A full stop/start is safer than an in-guest reboot for PCI device model changes.
- **Expected Output:**

```text
status: stopped
```

- **Verification:** `qm status ${VMID}` -> `stopped`.
- **⚠️ Caveats/Traps:** If shutdown fails because guest agent is not working, use `qm stop ${VMID}` only as a last resort.

**Step 2: Add PCI passthrough device**

- **Purpose:** Give Ubuntu direct ownership of the GPU.
- **Command(s):**

```bash
qm set ${VMID} -hostpci0 ${GPU_SLOT},pcie=1
qm start ${VMID}
```

- **Explanation:** `${GPU_SLOT}` should be the slot such as `01:00`; all-functions passthrough is preferred from the GUI when available.
- **Expected Output:**

```text
update VM ${VMID}: -hostpci0 ${GPU_SLOT},pcie=1
```

- **Verification:** Inside Ubuntu: `lspci -nn | grep -i nvidia` -> NVIDIA device visible.
- **⚠️ Caveats/Traps:** Initially keep `Primary GPU` disabled unless the VM needs physical display output.

### 3. Configuration Files

VM config path:

```text
/etc/pve/qemu-server/${VMID}.conf
```

Expected excerpt:

```text
machine: q35
bios: ovmf
hostpci0: ${GPU_SLOT},pcie=1
```

### 4. Troubleshooting & Recovery

- If VM fails to start, remove passthrough: `qm set ${VMID} -delete hostpci0`.
- If Ubuntu does not show NVIDIA, verify VFIO binding and VM hardware config.
- If console becomes unusable, keep SSH and virtual display available during initial setup.
