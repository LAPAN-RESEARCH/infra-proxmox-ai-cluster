import requests
from typing import List
from .base import Paper

def search_semantic_scholar(query: str, max_results: int = 15) -> List[Paper]:
    """Busca no Semantic Scholar via API pública com TLDR e contagem de citações."""
    base_url = "https://api.semanticscholar.org/graph/v1/paper/search"
    fields = "title,authors,abstract,year,externalIds,url,openAccessPdf,citationCount,venue,tldr"
    papers: List[Paper] = []

    try:
        res = requests.get(
            base_url,
            params={
                "query": query,
                "limit": max_results,
                "fields": fields
            },
            timeout=15
        )
        res.raise_for_status()
        data = res.json().get("data", [])

        for item in data:
            title = item.get("title", "").strip()
            authors = [a.get("name", "") for a in item.get("authors", []) if "name" in a]
            abstract = item.get("abstract") or ""
            year = item.get("year")
            ext_ids = item.get("externalIds") or {}
            doi = ext_ids.get("DOI")
            url = item.get("url") or f"https://www.semanticscholar.org/paper/{item.get('paperId')}"
            
            oa_pdf = item.get("openAccessPdf") or {}
            pdf_url = oa_pdf.get("url")
            
            citation_count = item.get("citationCount")
            tldr_dict = item.get("tldr") or {}
            tldr = tldr_dict.get("text")
            journal = item.get("venue") or ""

            papers.append(Paper(
                title=title,
                authors=authors,
                abstract=abstract,
                year=year,
                doi=doi,
                source="semanticscholar",
                url=url,
                pdf_url=pdf_url,
                journal=journal,
                citation_count=citation_count,
                tldr=tldr
            ))
    except Exception as e:
        print(f"[Aviso] Falha na busca Semantic Scholar: {e}")

    return papers
