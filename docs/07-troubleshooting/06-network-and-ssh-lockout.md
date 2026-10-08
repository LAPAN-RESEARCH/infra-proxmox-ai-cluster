# Network and SSH Lockout

## 1. Objective & Prerequisites

- Provide focused recovery steps for a known failure mode.
- Required previous state: access to either Proxmox host shell or Ubuntu VM shell, as specified.
- Estimated time: variable. Risk level: medium to high.

## 2. Step-by-Step Execution

### Step 1: Use existing session or console

- **Purpose:** Avoid losing the only control channel while repairing SSH/networking.
- **Command(s):**

```bash
ip -br addr
systemctl status ssh --no-pager
sudo ufw status verbose
```

- **Explanation:** Check IP, SSH service state, and firewall rules.
- **Expected Output:**

```text
ssh.service active (running)
22/tcp ALLOW IN ${LAN_CIDR}
```

- **Verification:** Open a second SSH session.
- **⚠️ Caveats/Traps:** Do not close the working session until the second one works.

### Step 2: Recover SSH config

- **Purpose:** Restore login if hardening was too aggressive.
- **Command(s):**

```bash
sudo cp /etc/ssh/sshd_config.bak /etc/ssh/sshd_config
sudo systemctl restart ssh
```

- **Explanation:** Reverts to the backup taken before hardening.
- **Expected Output:**

```text
No output on success.
```

- **Verification:** `ssh ${VM_USER}@${VM_IP}` -> Login works.
- **⚠️ Caveats/Traps:** If password login is disabled and keys are absent, console access is required.

### Step 3: Disable UFW temporarily if needed

- **Purpose:** Restore access during recovery.
- **Command(s):**

```bash
sudo ufw disable
```

- **Explanation:** Temporarily removes firewall enforcement while fixing rules.
- **Expected Output:**

```text
Firewall stopped and disabled on system startup
```

- **Verification:** SSH login works, then re-enable correct rules.
- **⚠️ Caveats/Traps:** Re-enable firewall after repair.

## 3. Configuration Files

- `/etc/netplan/01-ai-vm.yaml`
- `/etc/ssh/sshd_config`

## 4. Troubleshooting & Recovery

- If Netplan is broken, fix via Proxmox console and `sudo netplan apply`.
- If UFW blocks SSH, use console and disable UFW.
- If noVNC copy/paste is unreliable, use xterm.js serial console or SSH.
