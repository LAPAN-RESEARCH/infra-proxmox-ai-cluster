from typing import List

try:
    from engines.base import Paper
except (ImportError, ValueError):
    from ..engines.base import Paper


def generate_markdown_report(query: str, papers: List[Paper]) -> str:
    """Gera um relatório de revisão bibliográfica estruturado em Markdown."""
    lines = []
    lines.append(f"# Relatório de Revisão Bibliográfica: {query}")
    lines.append("")
    lines.append(f"**Total de artigos consolidados e deduplicados:** {len(papers)}")
    lines.append("")
    
    # Fontes
    sources_count = {}
    for p in papers:
        sources_count[p.source] = sources_count.get(p.source, 0) + 1
    
    lines.append("### Distribuição por Fonte de Dados:")
    for src, count in sorted(sources_count.items()):
        lines.append(f"- **{src.upper()}:** {count} artigos")
    lines.append("")

    # Tabela de evidências
    lines.append("## Tabela de Artigos Encontrados")
    lines.append("")
    lines.append("| Ano | Primeiro Autor | Título | Periódico / Fonte | Citações | DOI / Link | PDF OA |")
    lines.append("| :--- | :--- | :--- | :--- | :---: | :--- | :---: |")

    for p in papers:
        year_str = str(p.year) if p.year else "s.d."
        author_str = p.authors[0].split()[-1] if p.authors else "Anon"
        if len(p.authors) > 1:
            author_str += " et al."
        
        title_str = p.title.replace("|", "/")
        journal_str = (p.journal or p.source).replace("|", "/")
        citations_str = str(p.citation_count) if p.citation_count is not None else "-"
        
        link_str = f"[{p.doi}]({p.url})" if p.doi else f"[Link]({p.url})" if p.url else "-"
        pdf_str = f"[PDF]({p.pdf_url})" if p.pdf_url else "Não"

        lines.append(f"| {year_str} | {author_str} | {title_str} | {journal_str} | {citations_str} | {link_str} | {pdf_str} |")

    lines.append("")
    lines.append("## Resumos e Síntese de Conteúdo")
    lines.append("")

    for i, p in enumerate(papers, start=1):
        lines.append(f"### {i}. {p.title}")
        author_list = ", ".join(p.authors[:5]) if p.authors else "Autores não listados"
        if len(p.authors) > 5:
            author_list += f" (+ {len(p.authors)-5} outros)"
        lines.append(f"- **Autores:** {author_list}")
        lines.append(f"- **Ano:** {p.year or 'N/A'} | **Fonte original:** `{p.source}`")
        if p.journal:
            lines.append(f"- **Periódico:** {p.journal}")
        if p.doi:
            lines.append(f"- **DOI:** `{p.doi}`")
        if p.tldr:
            lines.append(f"- **TLDR (Síntese IA):** *{p.tldr}*")
        if p.abstract:
            lines.append(f"- **Resumo:**")
            lines.append(f"  > {p.abstract[:800]}..." if len(p.abstract) > 800 else f"  > {p.abstract}")
        lines.append("")

    return "\n".join(lines)
