# Architecture and Usage Guide

## 1. Operating Model

The Proxmox host is only the hypervisor. The Ubuntu VM `lapan-ai` is the AI appliance. Persistent AI state belongs under `/srv/ai`, and all application services run as Docker containers bound to `127.0.0.1`.

```mermaid
flowchart TD
    Host[Proxmox host] --> VM[Ubuntu VM lapan-ai]
    VM --> GPU[RTX 5060 Ti passthrough]
    VM --> Data[/srv/ai data disk]
    VM --> Docker[Docker Engine]
    Docker --> Ollama[Ollama LLMs and embeddings]
    Docker --> Speaches[Speaches Whisper STT]
    Docker --> WebUI[Open WebUI]
    Docker --> Qdrant[Qdrant vector DB]
    Docker --> Neo4j[Neo4j graph DB]
    Docker --> Jupyter[JupyterLab research workspace]
    Jupyter --> RAG[RAG ingestion and reranking]
    RAG --> Qdrant
    RAG --> Neo4j
    RAG --> Zotero[Zotero exports and PDFs]
    RAG --> Agents[Local agents and audit]
```

## 2. Service Map

| Service | Local URL | Main use | Persistent data |
| --- | --- | --- | --- |
| Ollama | `http://127.0.0.1:11434` | Local chat, coding, embeddings | `/srv/ai/ollama` |
| Open WebUI | `http://127.0.0.1:3000` | Browser UI for Ollama | `/srv/ai/open-webui` |
| Speaches | `http://127.0.0.1:8000` | Local Whisper transcription | `/srv/ai/models/huggingface`, `/srv/ai/logs/speaches` |
| Qdrant | `http://127.0.0.1:6333` | Vector search for RAG | `/srv/ai/qdrant/storage` |
| Neo4j | `http://127.0.0.1:7474`, `bolt://127.0.0.1:7687` | Semantic graph and provenance | `/srv/ai/neo4j` |
| JupyterLab | `http://127.0.0.1:8888` | Ingestion, notebooks, benchmarks | `/srv/ai/jupyter/work`, `/srv/ai/rag`, `/srv/ai/ingest` |

Remote use should go through SSH or Tailscale SSH tunnels, not public service binds:

```bash
ssh -L 3000:127.0.0.1:3000 \
    -L 8888:127.0.0.1:8888 \
    -L 11434:127.0.0.1:11434 \
    -L 8000:127.0.0.1:8000 \
    -L 6333:127.0.0.1:6333 \
    -L 7474:127.0.0.1:7474 \
    hugo@192.168.100.60
```

## 3. Daily Workflows

### Start and validate the stack

```bash
cd /srv/ai/compose/core
sudo docker compose --env-file .env up -d
sudo docker compose ps
/home/hugo/proxmox-lapan-ai-setup/scripts/validate_stack.sh
```

Use the root-owned maintenance wrapper from the remediation plan when noninteractive validation is required:

```bash
sudo -n /usr/local/sbin/lapan-ai-validate
```

### Use local LLMs and embeddings

```bash
curl -fsS http://127.0.0.1:11434/api/tags
curl -fsS http://127.0.0.1:11434/api/embed \
  -d '{"model":"bge-m3","input":"Fasciola hepatica intermediate host ecology"}'
```

Use Open WebUI at `http://127.0.0.1:3000` through the SSH tunnel for interactive chat. Keep model pulls limited and check `/srv/ai` capacity first.

### Use local transcription

```bash
source /srv/ai/compose/core/.env
curl -fsS -H "Authorization: Bearer ${SPEACHES_API_KEY}" \
  http://127.0.0.1:8000/v1/models

curl -fsS -H "Authorization: Bearer ${SPEACHES_API_KEY}" \
  http://127.0.0.1:8000/v1/audio/transcriptions \
  -F "file=@/path/to/test-audio.wav" \
  -F "model=${SPEACHES_MODEL}"
```

Keep audio and transcripts local. Do not paste patient or private research data into cloud services.

**Build and query RAG**
Run the bootstrap first to create the Qdrant collection, Neo4j constraints, and live config files:

```bash
/home/hugo/proxmox-lapan-ai-setup/scripts/setup_research_platform.sh
```

1. Export Zotero metadata to `/srv/ai/zotero/exports/library.bib`.
2. Place or link PDFs under `/srv/ai/zotero/pdfs`.
3. Parse source files into `/srv/ai/ingest/parsed`.
4. Chunk with provenance into `/srv/ai/ingest/chunks` and `/srv/ai/ingest/metadata`.
5. Embed with Ollama `bge-m3` and write vectors to Qdrant collection `${RAG_COLLECTION:-research_chunks_bge_m3}`.
6. Retrieve with BM25 plus dense vector search, rerank candidates with `${RERANKER_MODEL:-BAAI/bge-reranker-v2-m3}`, and pass only cited chunks to the LLM.
7. Save benchmark questions and retrieval results under `/srv/ai/rag/benchmarks`.

### Use the graph

```bash
source /srv/ai/compose/core/.env
neo4j_password="${NEO4J_AUTH#neo4j/}"
sudo docker exec -it neo4j cypher-shell -u neo4j -p "${neo4j_password}" 'SHOW CONSTRAINTS;'
```

Use Neo4j for entities, relationships, taxonomies, and provenance. Every graph claim should link back to a source document or chunk.

### Use local agents

Agents work under `/srv/ai/agents`. Use role-specific workspaces, keep policies in `/srv/ai/agents/policies`, and write append-only tool logs to `/srv/ai/agents/audit`. Research and clinical agents should be read/query/write-scratch only by default; do not mount the Docker socket into agent runtimes.

## 4. Storage and Maintenance Rules

- `/` is for the OS, packages, and small config only.
- `/srv/ai/docker` is Docker's data root.
- `/srv/ai/ollama` is Ollama's model store.
- `/srv/ai/models/huggingface` is the shared Hugging Face cache for Speaches and rerankers.
- `/srv/ai/backups` stores local backup archives; copy important archives off-machine.
- Stop Docker before moving model or Docker storage.

Routine checks:

```bash
df -h / /srv/ai
swapon --show
nvidia-smi
sudo docker system df
sudo du -sh /srv/ai/ollama /srv/ai/models/huggingface /srv/ai/docker /srv/ai/qdrant /srv/ai/neo4j 2>/dev/null
```

Back up before major changes:

```bash
/home/hugo/proxmox-lapan-ai-setup/scripts/backup_ai_stack.sh
tar -tzf /srv/ai/backups/ai-stack-*.tar.gz | head
```

## 5. Failure Rules

- If `/srv/ai` is not mounted, stop Docker before pulling models or building images.
- If Ollama loads on CPU, validate the Docker NVIDIA runtime and recreate the Ollama container.
- If Speaches lists no models, run `/home/hugo/proxmox-lapan-ai-setup/scripts/install_whisper_service.sh` and check `/srv/ai/models/huggingface`.
- If Qdrant returns `401`, use `api-key: ${QDRANT_API_KEY}`.
- If Neo4j auth fails, read the password from `NEO4J_AUTH` in the live `.env`.
- If an agent writes outside its workspace or lacks audit logs, disable it until the policy is fixed.
