# Current Status

## Working

- Proxmox stable
- IOMMU working
- VFIO working
- GPU passthrough working
- Ubuntu VM stable
- NVIDIA visible inside VM
- AVX/AVX2 visible inside VM
- Polars warning resolved
- Docker stack partially operational

## Pending

- Fix Proxmox storage layout
- Move VM disks off local
- Mount /srv/ai correctly
- Move Docker root to /srv/ai/docker
- Restart AI stack
- Re-download Ollama models safely

---

# Recommended Next Steps

1. Expand Proxmox root LV temporarily.
2. Inspect LVM thin pool.
3. Create proper Proxmox VM storage.
4. Move VM disks away from local.
5. Mount Ubuntu 500 GB disk as /srv/ai.
6. Move Docker data-root.
7. Restart containers.
8. Pull Ollama models again.
9. Begin RAG pipeline implementation.
