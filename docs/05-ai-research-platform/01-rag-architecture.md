# RAG Architecture

### 1. Objective & Prerequisites

- Define the local research retrieval pipeline for papers, notes, and later clinical documents.
- Required previous state: AI services running; Qdrant and Jupyter available.
- Estimated time: design phase 30 minutes; implementation separate. Risk level: low.

### 2. Step-by-Step Execution

**Step 1: Create canonical document records**

- **Purpose:** Preserve provenance from source file to chunk to answer.
- **Command(s):**

```bash
mkdir -p /srv/ai/ingest/{raw,parsed,chunks,metadata}
```

- **Explanation:** Separate raw inputs from parsed outputs and chunk metadata.
- **Expected Output:**

```text
No output on success.
```

- **Verification:** `find /srv/ai/ingest -maxdepth 2 -type d` -> Shows expected folders.
- **⚠️ Caveats/Traps:** Do not overwrite source PDFs; treat them as immutable inputs.

**Step 2: Use hybrid retrieval**

- **Purpose:** Combine keyword and semantic search for scientific precision.
- **Command(s):**

```bash
# Implementation placeholder in notebooks or future service:
# BM25 top-k + dense embedding top-k + deduplication + reranking
```

- **Explanation:** BM25 handles exact terms; embeddings handle paraphrases; reranking selects final evidence.
- **Expected Output:**

```text
[MISSING] Retrieval benchmark output.
```

- **Verification:** Create a small benchmark of paper questions and expected source chunks.
- **⚠️ Caveats/Traps:** Do not use embedding top-5 directly as final evidence for scientific claims.

### 3. Configuration Files

Future RAG config should live under:

```text
/srv/ai/rag/configs/
```

### 4. Troubleshooting & Recovery

- If answers hallucinate citations, inspect chunk provenance.
- If exact scientific terms are missed, strengthen BM25/sparse retrieval.
- If semantically similar but wrong passages are retrieved, add reranking and filters.
