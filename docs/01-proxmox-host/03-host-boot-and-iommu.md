# Host Boot and IOMMU

### 1. Objective & Prerequisites

- Configure kernel parameters required for stable headless Proxmox and IOMMU passthrough mode.
- Required previous state: BIOS virtualization features enabled.
- Estimated time: 15 minutes plus reboot. Risk level: medium.

### 2. Step-by-Step Execution

**Step 1: Edit GRUB**

- **Purpose:** Add the validated kernel parameters used by this host.
- **Command(s):**

```bash
vim /etc/default/grub
```

- **Explanation:** Use `configs/proxmox/grub.example`. The accepted parameter set is `quiet nomodeset iommu=pt modprobe.blacklist=nouveau`.
- **Expected Output:**

```text
GRUB_CMDLINE_LINUX_DEFAULT="quiet nomodeset iommu=pt modprobe.blacklist=nouveau"
```

- **Verification:** `grep GRUB_CMDLINE_LINUX_DEFAULT /etc/default/grub` -> Shows the expected string.
- **⚠️ Caveats/Traps:** Do not add `amd_iommu=on`; this host reported it as an unknown AMD-Vi option.

**Step 2: Update GRUB and reboot**

- **Purpose:** Apply bootloader changes to the next boot.
- **Command(s):**

```bash
update-grub
reboot
```

- **Explanation:** `update-grub` regenerates the bootloader menu. Reboot is required for kernel parameters.
- **Expected Output:**

```text
Generating grub configuration file ...
done
```

- **Verification:** `cat /proc/cmdline` -> Contains `iommu=pt` and `modprobe.blacklist=nouveau`.
- **⚠️ Caveats/Traps:** Reboot only after confirming the network config is stable.

**Step 3: Validate IOMMU**

- **Purpose:** Confirm that Linux detects IOMMU support.
- **Command(s):**

```bash
journalctl -k -b | grep -Ei 'iommu|amd-vi'
```

- **Explanation:** Kernel log lines show whether AMD-Vi/IOMMU initialized correctly.
- **Expected Output:**

```text
... iommu: Default domain type: Passthrough
...
```

- **Verification:** `journalctl -k -b | grep -i 'Default domain type: Passthrough'` -> Confirms passthrough domain mode.
- **⚠️ Caveats/Traps:** Some IOMMU messages are informational warnings; do not change working GRUB parameters unless passthrough fails.

### 3. Configuration Files

Reference: `configs/proxmox/grub.example`.

### 4. Troubleshooting & Recovery

- If the host reports `AMD-Vi: Unknown option - 'on'`, remove `amd_iommu=on`.
- If nouveau loads, verify both GRUB blacklist and `/etc/modprobe.d/blacklist-nouveau.conf`.
- If the host does not boot, use GRUB edit mode to temporarily remove the last changed parameter.
