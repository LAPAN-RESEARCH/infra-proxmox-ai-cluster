# Zotero Ingestion

## 1. Objective & Prerequisites

- Use Zotero as the source of truth while building a local searchable index.
- Required previous state: `/srv/ai/zotero` exists and the user has exported or synced Zotero metadata.
- Estimated time: 30-60 minutes. Risk level: low if read-only.

## 2. Step-by-Step Execution

### Step 1: Use exported metadata

- **Purpose:** Avoid brittle direct writes to Zotero internals.
- **Command(s):**

```bash
mkdir -p /srv/ai/zotero/{exports,pdfs}
ls -lah /srv/ai/zotero
```

- **Explanation:** Better BibTeX or CSL JSON exports can be placed under `exports`; PDFs can be linked or mirrored under `pdfs`.
- **Expected Output:**

```text
exports/
pdfs/
```

- **Verification:** A metadata export file exists, for example `/srv/ai/zotero/exports/library.bib`.
- **⚠️ Caveats/Traps:** Do not flatten all PDFs into one folder as the source of truth; preserve Zotero metadata and citation keys.

### Step 2: Mount Zotero read-only into Jupyter

- **Purpose:** Prevent notebooks or agents from modifying source library files.
- **Command(s):**

```bash
grep -n '/srv/ai/zotero' /srv/ai/compose/core/docker-compose.yml
```

- **Explanation:** The Compose stack should mount Zotero data read-only into Jupyter.
- **Expected Output:**

```text
- /srv/ai/zotero:/srv/ai/zotero:ro
```

- **Verification:** Inside Jupyter container, writes to `/srv/ai/zotero` should fail.
- **⚠️ Caveats/Traps:** Clinical or private notes should be indexed only by local-only tools.

## 3. Configuration Files

Future Zotero ingestion config:

```yaml
zotero:
  metadata_export: /srv/ai/zotero/exports/library.bib
  pdf_root: /srv/ai/zotero/pdfs
  read_only: true
```

## 4. Troubleshooting & Recovery

- If citation keys are missing, verify Better BibTeX export settings.
- If PDF paths break, use stable linked attachment base paths.
- If the ingestion pipeline modifies Zotero files, correct mounts to read-only.
