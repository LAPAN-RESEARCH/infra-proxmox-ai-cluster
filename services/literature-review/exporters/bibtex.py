import re
from typing import List

try:
    from engines.base import Paper
except (ImportError, ValueError):
    from ..engines.base import Paper



def sanitize_key(title: str, year: int = None, first_author: str = None) -> str:
    author_part = "anon"
    if first_author:
        last = first_author.split()[-1]
        author_part = re.sub(r'[^a-zA-Z0-9]', '', last).lower()
    
    year_part = str(year) if year else "nd"
    
    title_words = re.sub(r'[^a-zA-Z0-9\s]', '', title).split()
    title_part = title_words[0].lower() if title_words else "paper"
    
    return f"{author_part}_{year_part}_{title_part}"

def export_bibtex(papers: List[Paper]) -> str:
    """Gera bloco BibTeX completo e formatado para Zotero / Better BibTeX."""
    entries = []
    seen_keys = set()

    for paper in papers:
        first_author = paper.authors[0] if paper.authors else None
        base_key = sanitize_key(paper.title, paper.year, first_author)
        key = base_key
        counter = 1
        while key in seen_keys:
            key = f"{base_key}_{counter}"
            counter += 1
        seen_keys.add(key)

        author_str = " and ".join(paper.authors) if paper.authors else "Unknown"
        journal_str = paper.journal or (f"{paper.source.capitalize()} Repository" if paper.source else "Academic Paper")
        
        entry = [
            f"@article{{{key},",
            f"  title = {{{{{paper.title}}}}},",
            f"  author = {{{author_str}}},",
        ]
        
        if paper.year:
            entry.append(f"  year = {{{paper.year}}},")
        if journal_str:
            entry.append(f"  journal = {{{journal_str}}},")
        if paper.doi:
            entry.append(f"  doi = {{{paper.doi}}},")
        if paper.url:
            entry.append(f"  url = {{{paper.url}}},")
        if paper.abstract:
            clean_abstract = paper.abstract.replace("{", "").replace("}", "")
            entry.append(f"  abstract = {{{clean_abstract}}},")

        entry.append("}")
        entries.append("\n".join(entry))

    return "\n\n".join(entries)
