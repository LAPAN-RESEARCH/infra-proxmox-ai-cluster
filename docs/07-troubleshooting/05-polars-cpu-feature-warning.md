# Polars CPU Feature Warning

### 1. Objective & Prerequisites

- Provide focused recovery steps for a known failure mode.
- Required previous state: access to either Proxmox host shell or Ubuntu VM shell, as specified.
- Estimated time: variable. Risk level: medium to high.

### 2. Step-by-Step Execution

**Step 1: Check CPU flags in VM**

- **Purpose:** Confirm whether the VM exposes AVX/AVX2/FMA features required by modern scientific packages.
- **Command(s):**

```bash
lscpu | grep -i flags | grep -Eo 'avx2|avx|fma|bmi1|bmi2|abm|movbe|pclmulqdq' | sort -u
```

- **Explanation:** Missing flags indicate an overly conservative Proxmox CPU model.
- **Expected Output:**

```text
abm
avx
avx2
bmi1
bmi2
fma
movbe
pclmulqdq
```

- **Verification:** Polars imports without CPU warning.
- **⚠️ Caveats/Traps:** Do not hide the warning with `POLARS_SKIP_CPU_CHECK`.

**Step 2: Set VM CPU to host**

- **Purpose:** Expose the real Ryzen CPU feature set to Ubuntu.
- **Command(s):**

```bash
qm shutdown ${VMID}
qm set ${VMID} --cpu host
qm start ${VMID}
```

- **Explanation:** `cpu: host` provides best local performance at the cost of migration portability.
- **Expected Output:**

```text
update VM ${VMID}: -cpu host
```

- **Verification:** `qm config ${VMID} | grep '^cpu:'` -> `cpu: host`.
- **⚠️ Caveats/Traps:** A full VM stop/start is required; guest reboot may not be enough.

### 3. Configuration Files

Proxmox VM config excerpt:

```text
cpu: host
```

### 4. Troubleshooting & Recovery

- If flags remain missing, verify the host has them in `/proc/cpuinfo`.
- If VM migration is needed later, switch to a compatible CPU model temporarily.
- If a container still warns, restart the container after CPU model change.
