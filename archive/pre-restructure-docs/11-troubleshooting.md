
# Lessons Learned

## Important Operational Lessons

### 1. Keep Proxmox Minimal

The Proxmox host should:

- remain headless
- avoid NVIDIA drivers
- avoid unnecessary services
- avoid Tailscale initially

### 2. Use cpu: host

AI workloads require full CPU feature exposure.

### 3. Do Not Store Large VM Disks on local

`local` maps to:

```text
/var/lib/vz
```

which lives on the Proxmox root filesystem.

### 4. Move Docker Data to Dedicated Storage

Critical:

```text
/srv/ai/docker
```

### 5. Verify Mounts Before Pulling Models

Always check:

```bash
findmnt /srv/ai
sudo docker info | grep "Docker Root Dir"
df -h
```

before downloading large Ollama models.

---
