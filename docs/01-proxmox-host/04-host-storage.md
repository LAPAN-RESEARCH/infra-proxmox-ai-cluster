# Host Storage

## 1. Objective & Prerequisites

- Ensure VM disks live on Proxmox VM storage, not on the host root filesystem.
- Required previous state: Proxmox host reachable; VM stopped for disk moves.
- Estimated time: 15-60 minutes. Risk level: high if moving disks without backup.

## 2. Step-by-Step Execution

### Step 1: Check Proxmox storage

- **Purpose:** Detect whether large VM disks are on `local` or `local-lvm`.
- **Command(s):**

```bash
pvesm status
qm config ${VMID} | grep -E 'scsi|virtio|sata|ide|efidisk'
df -h /
```

- **Explanation:** `local` is directory storage on `/var/lib/vz`; `local-lvm` is the LVM-thin pool intended for VM disks.
- **Expected Output:**

```text
Name         Type     Status     Total       Used       Available     %
local        dir      active     64695968    5843908    55638640      9.03%
local-lvm    lvmthin  active     891289600   56775147   834514452     6.37%

scsi0: local-lvm:vm-2020-disk-0,iothread=1,size=100G
scsi1: local-lvm:vm-2020-disk-1,iothread=1,size=500G
```

- **Verification:** Large VM disks should be on `local-lvm`.
- **⚠️ Caveats/Traps:** A small EFI disk may remain on `local`; this is not the same risk as storing 100G/500G qcow2 data disks on `local`.

### Step 2: Inspect LVM-thin health

- **Purpose:** Confirm the thin pool has capacity and metadata headroom.
- **Command(s):**

```bash
lvs -a -o lv_name,vg_name,lv_size,lv_attr,origin,data_percent,metadata_percent,devices
```

- **Explanation:** LVM-thin pools can fail if data or metadata fills.
- **Expected Output:**

```text
data            lapan-vg 850.00g twi-aotz--  6.37  12.15
vm-2020-disk-0  lapan-vg 100.00g Vwi-aotz-- 42.09
vm-2020-disk-1  lapan-vg 500.00g Vwi-aotz--  2.41
```

- **Verification:** `data_percent` and `metadata_percent` are far below 80%.
- **⚠️ Caveats/Traps:** Thin-provisioned VM disks can appear large while using little physical space; still monitor the pool.

### Step 3: Move disks if they are still on `local`

- **Purpose:** Prevent host root exhaustion from VM disk growth.
- **Command(s):**

```bash
qm shutdown ${VMID}
qm disk move ${VMID} scsi0 local-lvm --delete 1
qm disk move ${VMID} scsi1 local-lvm --delete 1
qm start ${VMID}
```

- **Explanation:** `--delete 1` removes the old source disk after a successful move.
- **Expected Output:**

```text
transferred ...
successfully imported disk ...
```

- **Verification:** `qm config ${VMID}` shows `local-lvm` for `scsi0` and `scsi1`.
- **⚠️ Caveats/Traps:** Do not delete files from `/var/lib/vz/images` manually unless you have verified they are no longer referenced.

## 3. Configuration Files

Proxmox storage configuration:

```bash
cat /etc/pve/storage.cfg
```

Expected logical storage IDs:

```text
local
local-lvm
```

## 4. Troubleshooting & Recovery

- If `/` reaches 100%, stop the VM and run `apt clean`, `journalctl --vacuum-size=200M`, and remove stale `/var/tmp/pve-reserved-ports.tmp.*`.
- If `local-lvm` is missing but the `data` thin pool exists, add it with `pvesm add lvmthin local-lvm --vgname lapan-vg --thinpool data --content images,rootdir`.
- If `qm disk move` fails due to insufficient space, do not reboot; inspect `pvesm status`, `lvs`, and `df -h /`.
- If thin metadata approaches high usage, plan a maintenance window to extend metadata or reduce allocations.
