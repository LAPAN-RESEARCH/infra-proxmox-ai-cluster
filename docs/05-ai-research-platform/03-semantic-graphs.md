# Semantic Graphs

### 1. Objective & Prerequisites

- Define how Neo4j will store entities, relationships, taxonomies, and provenance.
- Required previous state: Neo4j container running and reachable through localhost tunnel.
- Estimated time: design 30 minutes; implementation later. Risk level: low.

### 2. Step-by-Step Execution

**Step 1: Validate Neo4j access**

- **Purpose:** Confirm graph database is ready before ingestion tooling is written.
- **Command(s):**

```bash
source /srv/ai/compose/core/.env
sudo docker exec -it neo4j cypher-shell -u neo4j -p "${NEO4J_AUTH#neo4j/}" 'RETURN 1 AS ok;'
```

- **Explanation:** `cypher-shell` verifies Bolt/auth and the database process.
- **Expected Output:**

```text
ok
1
```

- **Verification:** The query returns `1`.
- **⚠️ Caveats/Traps:** Do not commit real Neo4j passwords.

**Step 2: Use provenance-first graph schema**

- **Purpose:** Ensure every claim can be traced to a source chunk.
- **Command(s):**

```cypher
CREATE CONSTRAINT paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.doc_id IS UNIQUE;
CREATE CONSTRAINT chunk_id IF NOT EXISTS FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;
CREATE CONSTRAINT concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE;
```

- **Explanation:** Unique constraints prevent duplicate nodes during repeated ingestion.
- **Expected Output:**

```text
Added 3 constraints.
```

- **Verification:** `SHOW CONSTRAINTS;` -> Shows the expected constraints.
- **⚠️ Caveats/Traps:** LLM-extracted entities should not be automatically merged without alias review.

### 3. Configuration Files

Graph entity classes:

```text
Paper, Author, Chunk, Concept, Method, Dataset, Finding, ClinicalEntity
```

Core relationships:

```text
AUTHORED_BY, HAS_CHUNK, MENTIONS, USES_METHOD, STUDIES, SUPPORTED_BY, RELATED_TO
```

### 4. Troubleshooting & Recovery

- If duplicate concepts proliferate, add alias tables and human review.
- If graph claims cannot be audited, require `source_chunk_id` on every relationship.
- If Neo4j memory grows too large, tune heap and page cache in Compose.
