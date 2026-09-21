# Host Networking

### 1. Objective & Prerequisites

- Configure a stable Proxmox bridge for LAN access and VM networking.
- Required previous state: Proxmox installed and physical NIC identified.
- Estimated time: 10 minutes. Risk level: high if remote access is the only access path.

### 2. Step-by-Step Execution

**Step 1: Identify the physical NIC**

- **Purpose:** Confirm which interface should be enslaved into `vmbr0`.
- **Command(s):**

```bash
ip -br link
ip -br addr
```

- **Explanation:** The physical NIC should be manual/no IP, while `vmbr0` owns the host IP.
- **Expected Output:**

```text
${PHYSICAL_NIC} UP ...
vmbr0           UP ${PROXMOX_HOST_IP}/${CIDR_PREFIX}
```

- **Verification:** `ip route` -> Default route should use `vmbr0`.
- **⚠️ Caveats/Traps:** Editing network remotely can lock you out. Keep local console access available.

**Step 2: Configure the bridge**

- **Purpose:** Provide a stable host IP and bridge VM traffic through the physical NIC.
- **Command(s):**

```bash
vim /etc/network/interfaces
ifreload -a
```

- **Explanation:** Use the sanitized example in `configs/proxmox/interfaces.example` and replace variables.
- **Expected Output:**

```text
No error output from ifreload -a.
```

- **Verification:** `ping -c 3 ${LAN_GATEWAY}` -> Successful gateway reachability.
- **⚠️ Caveats/Traps:** Do not put the IP address on both the physical NIC and bridge.

### 3. Configuration Files

Reference: `configs/proxmox/interfaces.example`.

Production file:

```text
/etc/network/interfaces
```

### 4. Troubleshooting & Recovery

- If host loses network, use physical console and restore the previous `/etc/network/interfaces`.
- If VMs have no network, verify the VM NIC is attached to `vmbr0`.
- If the host IP moves unexpectedly, check for DHCP clients on the host interface.
