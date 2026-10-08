# BIOS and Firmware

## 1. Objective & Prerequisites

- Enable motherboard features required for virtualization and GPU passthrough.
- Required previous state: physical access to firmware setup.
- Estimated time: 10-20 minutes. Risk level: low.

## 2. Step-by-Step Execution

### Step 1: Enable virtualization features

- **Purpose:** Allow Proxmox to run hardware-accelerated VMs and assign PCI devices to guests.
- **Command(s):**

```bash
# Firmware UI, not shell commands:
# SVM = Enabled
# IOMMU = Enabled
# Above 4G Decoding = Enabled
# Resizable BAR = Enabled
```

- **Explanation:** SVM enables AMD virtualization; IOMMU enables safe PCI passthrough; Above 4G Decoding and Resizable BAR support modern GPU address mapping.
- **Expected Output:**

```text
Manual confirmation recorded on 2026-06-03.
```

- **Verification:** `journalctl -k -b | grep -Ei 'iommu|amd-vi'` -> Kernel should report AMD-Vi/IOMMU availability after boot.
- **⚠️ Caveats/Traps:** Firmware labels vary by motherboard; do not disable CSM/UEFI settings blindly if the host already boots reliably.

## 3. Configuration Files

No Linux configuration files are modified in this phase.

## 4. Troubleshooting & Recovery

- If IOMMU is absent in Linux, recheck BIOS IOMMU and SVM.
- If GPU passthrough fails later with BAR errors, recheck Above 4G Decoding.
- If the host fails to boot after unrelated firmware changes, revert only the last firmware change and keep SVM/IOMMU enabled.
