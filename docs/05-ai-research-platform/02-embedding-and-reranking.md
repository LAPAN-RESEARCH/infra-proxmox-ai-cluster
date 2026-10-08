# Embedding and Reranking

## 1. Objective & Prerequisites

- Select local-only embedding and reranking defaults for retrieval quality.
- Required previous state: Ollama and/or Jupyter environment available.
- Estimated time: 30 minutes for initial tests. Risk level: low.

## 2. Step-by-Step Execution

### Step 1: Start with BGE-M3

- **Purpose:** Use a strong multilingual local default for English and Portuguese scientific text.
- **Command(s):**

```bash
sudo docker exec -it ollama ollama pull bge-m3
curl http://127.0.0.1:11434/api/embed -d '{"model":"bge-m3","input":"Fasciola hepatica intermediate host ecology"}'
```

- **Explanation:** BGE-M3 is the practical first embedding model for local hybrid RAG.
- **Expected Output:**

```text
{"model":"bge-m3", "embeddings": [[...]]}
```

- **Verification:** The API returns a numeric embedding array.
- **⚠️ Caveats/Traps:** Embedding dimension and model name must stay consistent per Qdrant collection.

### Step 2: Add reranking after baseline retrieval

- **Purpose:** Improve precision after BM25 + dense retrieval.
- **Command(s):**

```bash
# Future implementation placeholder:
# rerank top 30-50 candidate chunks and pass top 5-12 to LLM.
```

- **Explanation:** Rerankers evaluate query-passage relevance more directly than vector similarity.
- **Expected Output:**

```text
[MISSING] Reranker benchmark results.
```

- **Verification:** Compare baseline hybrid retrieval against reranked retrieval on known questions.
- **⚠️ Caveats/Traps:** Reranking is slower; use it after candidate retrieval, not over the entire corpus.

## 3. Configuration Files

Future embedding config example:

```yaml
embedding:
  provider: ollama
  model: bge-m3
  private_only: true
reranker:
  provider: local
  model: ${LOCAL_RERANKER_MODEL}
```

## 4. Troubleshooting & Recovery

- If retrieval quality is poor, inspect chunking before changing models.
- If Qdrant collection dimension mismatches, recreate the collection or use a separate collection.
- If embeddings are slow, test smaller models before buying more hardware.
