# Servidores MCP do Agente LAPAN

Os MCP servers são as ferramentas estruturadas do agente — preferíveis ao
`exec` bruto porque têm contrato estável (nome, parâmetros, saída previsível).
Todos os nove rodam como processos filhos do gateway (transporte stdio),
instalados na imagem via `uv tool install` e declarados em
`mcp.servers` do `openclaw.json`.

Os que precisam de credencial usam um **shim** (`/usr/local/bin/mcp-*.sh`) que
resolve segredos do ambiente do container — nunca do git.

## Mapa rápido: qual MCP para qual pergunta

| Se você quer... | Use |
| --- | --- |
| Achar artigos por tema em bases externas | `papers` |
| Consultar o acervo próprio (~5 mil itens) | `zotero` (ou CLI `zotero`) |
| Ler a seção de Métodos de um preprint | `arxiv` |
| Ensaio clínico, gene, variante, fármaco | `biomcp` |
| Ver quem citou um artigo / impacto | `semanticscholar` |
| Issue, PR, log de CI | `github` (ou `gh`) |
| Achar trecho exato já indexado dos PDFs | `qdrant` |
| Cruzar relações (autor↔método↔achado) | `neo4j` |
| Achar onde um símbolo é usado no código | `serena` |

---

## papers (paper-search-mcp)

**O que é:** busca e download de artigos acadêmicos em 20+ fontes: PubMed,
arXiv, bioRxiv, medRxiv, OpenAlex, Semantic Scholar, Europe PMC, Crossref,
CORE, Zenodo, DOAJ, Unpaywall etc.

**Para que serve no LAPAN:** descoberta de literatura *além* do acervo Zotero;
é o motor da varredura diária de publicações.

**Destaques:** `download_with_fallback` segue uma cadeia open-access
(fonte nativa → OpenAIRE/CORE/PMC → Unpaywall) para obter o PDF legalmente.
Chaves opcionais (`PAPER_SEARCH_MCP_*` no `.env`) elevam limites de taxa.
Email do Unpayway configurado no `openclaw.json` (identidade de contato).

## zotero (zotero-mcp)

**O que é:** acesso estruturado à biblioteca Zotero local — lê direto do
`zotero.sqlite` montado no container (modo local, com snapshot para não
travar o banco do desktop).

**Para que serve:** buscar por título/autor/coleção **e por significado**
(busca semântica com embeddings bge-m3 do Ollama), exportar BibTeX, extrair
anotações de PDF, ver metadados.

**Quando usar vs. CLI `zotero`:** o MCP para busca estruturada e BibTeX; o CLI
(`zotero read-pdf`) para leitura profunda com OCR de fallback — os dois se
complementam.

**Limitação:** escrita na biblioteca exige Zotero ≥10 com API local ou chave
web (`ZOTERO_API_KEY`) — hoje usamos somente leitura.

## arxiv (arxiv-mcp-server)

**O que é:** preprints do arXiv com um diferencial único: leitura do
**LaTeX fonte por seção** — dá para pedir só a seção *Methods* sem ruído do
PDF inteiro.

**Destaques:** `watch_topic` mantém vigilância persistente de tópicos;
`citation_graph` cruza referências via Semantic Scholar; export BibTeX.
Papers baixados ficam em `~/workspace/arxiv-papers/`.

## biomcp

**O que é:** ~70 fontes biomédicas num só servidor: PubMed, ClinicalTrials.gov
(ensaios com elegibilidade e desfechos), ClinVar, gnomAD, CIViC, GWAS Catalog,
MyGene, Reactome, OpenFDA, CPIC/PharmGKB.

**Para que serve no LAPAN:** a vertente clínica — oculomics, ERG,
farmacogenômica, desenho de estudo ("existem ensaios em recrutamento de ERG em
TDAH?"). Vencedor do St. Jude KIDS BioHackathon 2025. Chave opcional
`NCBI_API_KEY` eleva limites do PubMed.

## github (github-mcp-server oficial)

**O que é:** o servidor MCP oficial do GitHub (binário Go da própria GitHub,
versão pinada no Dockerfile). Toolsets restritos a `context, repos, issues,
pull_requests, actions` — **leitura + gestão de issues/PRs + CI**, sem push.

**Para que serve:** "o que quebrou no CI do research-cca?", "abra uma issue
sobre esse bug", "revê o diff do PR #12". Push e commit continuam via `git`
no `exec` (com as credenciais montadas). Autenticação: PAT opcional do `.env`
ou fallback para o token do `gh` do host — ver [07-seguranca.md](07-seguranca.md).

## qdrant (mcp-server-qdrant)

**O que é:** busca vetorial direto na coleção `research_chunks_bge_m3` — os
chunks dos PDFs já ingeridos pela plataforma de pesquisa (Docling → Qdrant).

**Para que serve:** recuperar o **trecho exato** de um paper já indexado
("onde mesmo que o artigo do Zhang define o critério de exclusão?"). Diferente
do `zotero` (metadados/anotações) e do RAG do `ai-api` (usado por aplicações
externas).

## neo4j (mcp-neo4j-cypher)

**O que é:** execução de queries Cypher no grafo de conhecimento da plataforma
(autores, artigos, conceitos, biomarcadores, metodologias).

**Para que serve:** relações e contradições — "quais artigos usaram o mesmo
paradigma mas concluíram diferente?". Complementa o IA-as-a-Judge:
o detector de inconsistências registra achados que podem ser modelados aqui.

## semanticscholar (semantic-scholar-mcp)

**O que é:** o grafo de citações do Semantic Scholar: quem citou, referências
estruturadas, artigos marcados como influentes, recomendações de leitura.

**Para que serve:** impacto e rastreabilidade — "quem citou o paper base do
rCCA desde 2024?". Chave opcional `SEMANTIC_SCHOLAR_API_KEY` no `.env` eleva
o limite de requisições.

## serena (Serena MCP)

**O que é:** análise e edição de código **semântica** via servidores de
linguagem (LSP) — 40+ linguagens, incluindo Python e TypeScript.

**Para que serve:** "onde `process_erg` é chamado e o que ele retorna?" —
resposta por símbolo, não por regex. Refatorações seguras (renomear símbolo,
achar implementações). Usa **antes** de delegar mudanças grandes a `agy`/`claude`
para dimensionar o impacto. Nota: baixa os language servers sob demanda na
primeira análise de um projeto (requer rede naquele momento).

---

## Gestão e troubleshooting

```bash
# listar servidores e status
sudo docker exec openclaw openclaw mcp status --verbose

# testar um servidor específico ao vivo
sudo docker exec openclaw openclaw mcp probe papers

# diagnóstico completo
sudo docker exec openclaw openclaw mcp doctor --probe
```

Sintoma comum: `rate limit` em `papers`/`semanticscholar` → configure as chaves
opcionais no `.env` (ver `configs/ai-stack/.env.example`). Erro de auth no
`github` → verifique `GITHUB_PERSONAL_ACCESS_TOKEN` ou o token do `gh` do host.
