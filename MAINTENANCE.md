# Maintenance Guide

## 1. Model Updates and Ollama Management

List models:

```bash
sudo docker exec -it ollama ollama list
```

Pull a model only after checking disk space:

```bash
df -h /srv/ai
sudo docker exec -it ollama ollama pull ${MODEL_NAME}
df -h /srv/ai
```

Remove an unused model:

```bash
sudo docker exec -it ollama ollama rm ${MODEL_NAME}
```

Recommended starting models:

```text
qwen3:8b
qwen2.5-coder:7b
bge-m3
embeddinggemma
```

## 2. Docker and NVIDIA Runtime Updates

Before updating:

```bash
cd /srv/ai/compose/core
sudo docker compose ps
nvidia-smi
sudo docker info | grep 'Docker Root Dir'
```

Update images (Automated script with disk check, backup, prune, and validation):

```bash
scripts/update_docker_stack.sh
```

Or manually:

```bash
cd /srv/ai/compose/core
sudo docker compose pull
sudo docker compose build --pull
sudo docker compose up -d
```


Update only the Whisper transcription service:

```bash
scripts/install_whisper_service.sh
```

Validate:

```bash
scripts/validate_stack.sh
```

## 3. Log Rotation

Docker log rotation is configured in `/etc/docker/daemon.json`:

```json
{
  "data-root": "/srv/ai/docker",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  }
}
```

Apply changes:

```bash
sudo systemctl restart docker
```

## 4. Backups

Run:

```bash
scripts/backup_ai_stack.sh
```

Minimum backup targets:

```text
/srv/ai/compose
/srv/ai/open-webui
/srv/ai/qdrant
/srv/ai/neo4j
/srv/ai/jupyter/work
/srv/ai/rag
/srv/ai/zotero/exports
/etc/docker/daemon.json
```

Large Ollama and Speaches/Hugging Face model files are usually re-downloadable and may be excluded from routine backups unless bandwidth is constrained.

## 5. Rollback GPU Passthrough

On Proxmox, stop the VM:

```bash
qm shutdown ${VMID}
```

Remove the passthrough device:

```bash
qm set ${VMID} -delete hostpci0
```

Start the VM:

```bash
qm start ${VMID}
```

Do not install NVIDIA drivers on the Proxmox host as a rollback strategy. The host should remain minimal.

## 6. Rollback NVIDIA Driver in Ubuntu

Inside the VM:

```bash
sudo apt purge 'nvidia-*' 'libnvidia-*'
sudo apt autoremove --purge -y
sudo apt install -y ubuntu-drivers-common
sudo ubuntu-drivers install --gpgpu
sudo reboot
```

Then validate:

```bash
nvidia-smi
sudo docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu24.04 nvidia-smi
```

## 7. Validation Logs

Current validation logs are archived at:

```text
archive/validation/host-state-20260521-164641.txt
archive/validation/vm-state-20260521-194735.txt
```

Use these as the baseline for future drift detection.

## 8. Roadmap Revision Policy

The old future roadmap is archived. Create a new roadmap only after collecting fresh host and VM state with:

```bash
VMID=${VMID} scripts/gather_host_state.sh
scripts/gather_vm_state.sh
```
