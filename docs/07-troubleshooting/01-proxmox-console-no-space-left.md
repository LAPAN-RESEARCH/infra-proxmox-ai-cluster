# Proxmox Console: No Space Left on Device

### 1. Objective & Prerequisites

- Recover Proxmox noVNC/xterm console failure caused by host root filesystem exhaustion.
- Required previous state: SSH access to Proxmox host or physical shell.
- Estimated time: 10-45 minutes. Risk level: medium.

### 2. Step-by-Step Execution

**Step 1: Confirm host root is full**

- **Purpose:** Distinguish Proxmox host exhaustion from Ubuntu VM exhaustion.
- **Command(s):**

```bash
df -h /
pvesm status
du -xhd1 /var/lib/vz 2>/dev/null | sort -h
```

- **Explanation:** Errors such as `/var/tmp/pve-reserved-ports.tmp.*` indicate host-side exhaustion.
- **Expected Output during failure:**

```text
/dev/mapper/lapan--vg-root  52G  52G  0  100% /
47G /var/lib/vz/images
```

- **Verification:** Root is full and VM images consume `/var/lib/vz`.
- **⚠️ Caveats/Traps:** Do not delete VM disks manually.

**Step 2: Stop VM and free emergency space**

- **Purpose:** Stop VM disk growth and restore basic Proxmox operation.
- **Command(s):**

```bash
qm stop ${VMID}
apt clean
journalctl --vacuum-size=200M
rm -f /var/tmp/pve-reserved-ports.tmp.*
rm -rf /tmp/*
df -h /
```

- **Expected Output after recovery:**

```text
/dev/mapper/lapan--vg-root  62G  5.6G  54G  10% /
```

- **Verification:** Proxmox console can open again.
- **⚠️ Caveats/Traps:** Avoid rebooting while root is 100% unless there is no alternative.

**Step 3: Move VM disks to `local-lvm`**

- **Purpose:** Remove large VM disks from root-backed `local` storage.
- **Command(s):**

```bash
qm disk move ${VMID} scsi0 local-lvm --delete 1
qm disk move ${VMID} scsi1 local-lvm --delete 1
qm config ${VMID} | grep -E 'scsi|efidisk'
```

- **Expected Output:**

```text
scsi0: local-lvm:vm-2020-disk-0,iothread=1,size=100G
scsi1: local-lvm:vm-2020-disk-1,iothread=1,size=500G
```

- **Verification:** Large data disks are on `local-lvm`.
- **⚠️ Caveats/Traps:** The small EFI disk may remain on `local`.

### 3. Configuration Files

Relevant Proxmox storage config:

```bash
cat /etc/pve/storage.cfg
```

### 4. Troubleshooting & Recovery

- If `qm disk move` is unavailable, use `qm move_disk` on older syntax.
- If `local-lvm` is missing, inspect `lvs` for an existing `data` thin pool before creating anything.
- If thin-pool metadata is high, stop growing workloads and plan maintenance.
- If `/var/tmp` errors persist after freeing space, restart Proxmox proxy services only after confirming `/` has free space.
