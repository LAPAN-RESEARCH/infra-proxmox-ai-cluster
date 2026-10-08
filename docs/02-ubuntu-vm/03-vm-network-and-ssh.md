# VM Network and SSH

## 1. Objective & Prerequisites

- Configure reliable SSH administration and a static VM address.
- Required previous state: Ubuntu installed and reachable by Proxmox console.
- Estimated time: 20 minutes. Risk level: medium.

## 2. Step-by-Step Execution

### Step 1: Configure static network

- **Purpose:** Make the AI VM reachable at a predictable LAN address.
- **Command(s):**

```bash
ip -br link
sudo vim /etc/netplan/01-ai-vm.yaml
sudo netplan apply
```

- **Explanation:** Use `configs/ubuntu-vm/netplan.example.yaml`; replace `${VM_NIC_NAME}`, `${VM_IP}`, and DNS values.
- **Expected Output:**

```text
No error output from netplan apply.
```

- **Verification:** `ip -br addr` -> VM NIC shows `${VM_IP}/${CIDR_PREFIX}`.
- **⚠️ Caveats/Traps:** Keep console access open while applying Netplan changes.

### Step 2: Install SSH public key

- **Purpose:** Enable secure key-based administration.
- **Command(s):**

```bash
ssh-copy-id -i ~/.ssh/${PUBLIC_KEY_FILE}.pub ${VM_USER}@${VM_IP}
ssh -i ~/.ssh/${PRIVATE_KEY_FILE} ${VM_USER}@${VM_IP}
```

- **Explanation:** The comment at the end of the `.pub` key is only a label and need not match `${VM_USER}`.
- **Expected Output:**

```text
${VM_USER}@${VM_HOSTNAME}:~$
```

- **Verification:** Open a second SSH session before disabling password login.
- **⚠️ Caveats/Traps:** Never paste private keys into `authorized_keys`; only paste `.pub` content.

### Step 3: Harden SSH

- **Purpose:** Disable root and password login after key login is proven.
- **Command(s):**

```bash
sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak
sudo vim /etc/ssh/sshd_config
sudo systemctl restart ssh
```

- **Explanation:** Apply the settings from `configs/ubuntu-vm/sshd_config.hardening.example`.
- **Expected Output:**

```text
No output from systemctl restart ssh.
```

- **Verification:** `ssh -i ~/.ssh/${PRIVATE_KEY_FILE} ${VM_USER}@${VM_IP}` -> New key-based login works.
- **⚠️ Caveats/Traps:** Do not close the current SSH session until a second login succeeds.

### Step 4: Enable UFW for SSH only

- **Purpose:** Restrict inbound traffic to LAN SSH before service tunnels are used.
- **Command(s):**

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from ${LAN_CIDR} to any port 22 proto tcp
sudo ufw enable
sudo ufw status verbose
```

- **Explanation:** This allows SSH from the LAN subnet and denies other inbound traffic.
- **Expected Output:**

```text
22/tcp ALLOW IN ${LAN_CIDR}
```

- **Verification:** Open a second SSH connection from a LAN workstation.
- **⚠️ Caveats/Traps:** Docker-published ports need explicit localhost binding; do not rely only on UFW.

### Step 5: Install Tailscale for external access

- **Purpose:** Keep the VM static LAN IP for local services and add secure remote access from outside your network.
- **Command(s):**

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
tailscale ip -4
tailscale status
```

- **Explanation:** Tailscale creates `tailscale0` (overlay interface) and does not replace your Netplan static IP on the VM NIC. Use the Tailscale-assigned `100.x.y.z` address for remote access from outside.
- **Expected Output:**

```text
100.x.y.z
```

- **Verification:**
  - On the VM: `ip -br addr` -> `${VM_NIC_NAME}` still shows `${VM_IP}/${CIDR_PREFIX}`.
  - From an external client logged into the same tailnet: `ssh ${VM_USER}@<tailscale-ip>` succeeds.
- **⚠️ Caveats/Traps:**
  - Do not remove or alter your existing Netplan static config; Tailscale is additive.
  - Avoid `--accept-routes` unless you explicitly need subnet routes.
  - If UFW is enabled, allow traffic on `tailscale0`:

```bash
sudo ufw allow in on tailscale0
```

### Step 5.1 (Optional): Restrict Tailscale access with ACL + tags

- **Purpose:** Limit who can SSH to the VM over Tailscale while keeping LAN static-IP access unchanged.
- **Command(s):**

```bash
# On the VM, advertise a tag owned by admin users
sudo tailscale up --ssh --advertise-tags=tag:ai-vm

# Check that the tag is applied
tailscale status
```

- **Explanation:** Define ACL policy in the Tailscale admin panel so only approved users/groups can reach `tag:ai-vm` on port 22.
- **Expected Output:**

```text
Machine shows tag:ai-vm in tailscale status/admin panel.
```

- **Verification:**
  - Allowed user from outside: `ssh ${VM_USER}@<tailscale-ip>` works.
  - Non-allowed user: SSH is denied by tailnet ACL.
- **⚠️ Caveats/Traps:**
  - Tag ownership must be configured in tailnet policy (`tagOwners`) before tag advertisement succeeds.
  - ACLs apply only to Tailscale traffic; LAN access control still depends on local firewall/SSH settings.

## 3. Configuration Files

- `configs/ubuntu-vm/netplan.example.yaml`
- `configs/ubuntu-vm/sshd_config.hardening.example`

## 4. Troubleshooting & Recovery

- If SSH fails, use Proxmox console and revert `/etc/ssh/sshd_config.bak`.
- If UFW locks you out, use console and run `sudo ufw disable`.
- If DNS fails, check the Netplan nameserver section.
- If Tailscale login/state breaks, run `sudo tailscale down` then `sudo tailscale up --ssh` and re-check `tailscale status`.
