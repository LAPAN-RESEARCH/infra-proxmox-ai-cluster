# VFIO GPU Passthrough

## VFIO Modules

```text
vfio
vfio_iommu_type1
vfio_pci
```

## VFIO Binding

Example:

```text
options vfio-pci ids=10de:2d04,10de:XXXX disable_vga=1
```

---

# VM GPU Configuration

## PCI Passthrough

Configured in Proxmox:

```text
All Functions: yes
PCI-Express: yes
Primary GPU: no
ROM-Bar: on
```

Verification inside VM:

```bash
lspci -nn | grep -i nvidia
```

---
