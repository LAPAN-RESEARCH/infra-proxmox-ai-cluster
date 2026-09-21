# Local Agents

### 1. Objective & Prerequisites

- Define safe agent design after infrastructure and retrieval are stable.
- Required previous state: local models, retrieval, and audit logging available.
- Estimated time: design 30 minutes; implementation later. Risk level: high if tools are unrestricted.

### 2. Step-by-Step Execution

**Step 1: Split agents by task**

- **Purpose:** Avoid a single overpowered agent with broad filesystem and shell access.
- **Command(s):**

```bash
mkdir -p /srv/ai/agents/{coding,papers,graphs,clinical,audit,scratch}
```

- **Explanation:** Separate workspaces make permissions and audit easier.
- **Expected Output:**

```text
No output on success.
```

- **Verification:** `find /srv/ai/agents -maxdepth 1 -type d` -> Shows role-specific directories.
- **⚠️ Caveats/Traps:** Do not mount the Docker socket into agent containers.

**Step 2: Require tool allowlists**

- **Purpose:** Prevent destructive or privacy-violating tool use.
- **Command(s):**

```bash
# Future policy file placeholder:
# tools_allowed: read_file, write_scratch, query_qdrant, query_neo4j
# tools_denied: unrestricted_shell, docker_socket, internet_for_clinical_data
```

- **Explanation:** Agents should call narrow tools with logged inputs and outputs.
- **Expected Output:**

```text
[MISSING] Agent policy implementation.
```

- **Verification:** Every tool call should produce an audit log entry.
- **⚠️ Caveats/Traps:** Autonomous shell tools are not appropriate for clinical data workflows.

### 3. Configuration Files

Future agent policy example:

```yaml
agents:
  clinical_report:
    internet: false
    filesystem_root: /srv/ai/agents/clinical
    require_human_review: true
  coding:
    internet: false
    filesystem_root: /srv/ai/agents/coding
    shell: allowlisted
```

### 4. Troubleshooting & Recovery

- If an agent writes outside its workspace, disable the tool and inspect audit logs.
- If clinical output contains invented facts, enforce structured templates and missing-data fields.
- If coding agent changes are unsafe, require patch generation rather than direct writes.
