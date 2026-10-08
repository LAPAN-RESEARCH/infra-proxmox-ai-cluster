# Literature Review Engine — LAPAN AI

Serviço de automação de revisão bibliográfica científica multi-fonte integrado ao Zotero e ao OpenClaw.

## Funcionalidades

- **Busca federada em 5 bases acadêmicas:**
  - PubMed / NCBI (via E-utilities)
  - arXiv (via Atom API)
  - Semantic Scholar (via S2 API)
  - CrossRef (via REST API)
  - Europe PMC (com foco em artigos Open Access e preprints bioRxiv/medRxiv)
- **Deduplicação automática:** normalização e casamento por DOI e similaridade de títulos.
- **Exportação BibTeX padrão:** gera `references.bib` higienizado e formatado para Zotero / Better BibTeX.
- **Relatório de Síntese em Markdown:** tabela de evidências, resumos estruturados e contagem de citações.
- **Download de PDFs Open Access:** baixa preprints e artigos de acesso aberto automaticamente.
- **Integração com Zotero:** injeção direta de coleções e itens via `pyzotero`.

## Como Executar Localmente

```bash
# Busca padrão com relatório e BibTeX
python3 services/literature-review/review.py \
  --query "glaucoma deep learning optical coherence tomography" \
  --max-per-engine 15 \
  --output-dir ./revisao_glaucoma

# Busca com download de PDFs e injeção no Zotero
python3 services/literature-review/review.py \
  --query "retinal disease multimodal foundation models" \
  --download-pdfs \
  --zotero-collection "Fundamentos Retina" \
  --zotero-user-id "12946936" \
  --zotero-api-key "<SEU_TOKEN_DO_ZOTERO>" \
  --output-dir ./revisao_retina
```
