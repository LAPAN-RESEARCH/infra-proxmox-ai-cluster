# VFIO Host Binding

## 1. Objective & Prerequisites

- Bind the NVIDIA GPU functions to `vfio-pci` on Proxmox so the host does not claim them.
- Required previous state: IOMMU enabled and host boot stable.
- Estimated time: 20 minutes plus reboot. Risk level: high on single-GPU systems.

## 2. Step-by-Step Execution

### Step 1: Identify NVIDIA PCI IDs

- **Purpose:** Bind all GPU functions, including HDMI/DP audio, to VFIO.
- **Command(s):**

```bash
lspci -nn | grep -Ei 'nvidia|10de|vga|3d|display|audio'
```

- **Explanation:** The GPU and its audio function usually share the same PCI slot with different function numbers.
- **Expected Output:**

```text
${GPU_SLOT}.0 VGA compatible controller ... [${NVIDIA_GPU_PCI_ID}]
${GPU_SLOT}.1 Audio device ... [${NVIDIA_AUDIO_PCI_ID}]
```

- **Verification:** Record both IDs in `configs/proxmox/vfio.conf`.
- **⚠️ Caveats/Traps:** Binding only the VGA function can leave the audio function attached to the host and break passthrough.

### Step 2: Configure VFIO modules and binding

- **Purpose:** Ensure VFIO loads early and captures the GPU.
- **Command(s):**

```bash
cp configs/proxmox/modules-load-vfio.conf /etc/modules-load.d/vfio.conf
cp configs/proxmox/blacklist-nouveau.conf /etc/modprobe.d/blacklist-nouveau.conf
vim /etc/modprobe.d/vfio.conf
update-initramfs -u -k all
reboot
```

- **Explanation:** `update-initramfs` embeds early module and binding configuration into boot images.
- **Expected Output:**

```text
update-initramfs: Generating /boot/initrd.img-...
```

- **Verification:** `lspci -nnk -d 10de:` -> `Kernel driver in use: vfio-pci` for GPU functions.
- **⚠️ Caveats/Traps:** Proxmox host should not have NVIDIA drivers installed.

## 3. Configuration Files

`/etc/modules-load.d/vfio.conf`:

```text
vfio
vfio_iommu_type1
vfio_pci
```

`/etc/modprobe.d/vfio.conf`:

```text
options vfio-pci ids=${NVIDIA_GPU_PCI_ID},${NVIDIA_AUDIO_PCI_ID} disable_vga=1
```

## 4. Troubleshooting & Recovery

- If GPU still uses nouveau, verify blacklist and GRUB `modprobe.blacklist=nouveau`.
- If host boot becomes unstable, remove VFIO binding from recovery shell and rebuild initramfs.
- If IOMMU group is not isolated, inspect `find /sys/kernel/iommu_groups -type l` before considering ACS overrides.
