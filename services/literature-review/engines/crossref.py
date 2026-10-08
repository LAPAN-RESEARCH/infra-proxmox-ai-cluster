import requests
from typing import List
from .base import Paper

def search_crossref(query: str, max_results: int = 15) -> List[Paper]:
    """Busca no CrossRef via REST API oficial para periódicos acadêmicos e DOIs."""
    base_url = "https://api.crossref.org/works"
    papers: List[Paper] = []
    headers = {"User-Agent": "LAPAN-AI-ResearchReview/1.0 (mailto:pesquisa@lapan.local)"}

    try:
        res = requests.get(
            base_url,
            params={
                "query": query,
                "rows": max_results,
                "sort": "relevance"
            },
            headers=headers,
            timeout=15
        )
        res.raise_for_status()
        items = res.json().get("message", {}).get("items", [])

        for item in items:
            title_list = item.get("title", [])
            title = title_list[0].strip() if title_list else ""
            if not title:
                continue

            authors = []
            for author in item.get("author", []):
                given = author.get("given", "")
                family = author.get("family", "")
                name = f"{given} {family}".strip() or author.get("name", "")
                if name:
                    authors.append(name)

            abstract = item.get("abstract", "")
            # Limpar tags XML se presentes no abstract do CrossRef
            if "<jats:p>" in abstract:
                import re
                abstract = re.sub(r'<[^>]+>', '', abstract)

            year = None
            published = item.get("published-print") or item.get("published-online") or item.get("issued")
            if published and "date-parts" in published:
                date_parts = published["date-parts"]
                if date_parts and date_parts[0] and isinstance(date_parts[0][0], int):
                    year = date_parts[0][0]

            doi = item.get("DOI")
            url = item.get("URL") or (f"https://doi.org/{doi}" if doi else "")
            
            container = item.get("container-title", [])
            journal = container[0] if container else ""

            papers.append(Paper(
                title=title,
                authors=authors,
                abstract=abstract,
                year=year,
                doi=doi,
                source="crossref",
                url=url,
                journal=journal,
                citation_count=item.get("is-referenced-by-count")
            ))
    except Exception as e:
        print(f"[Aviso] Falha na busca CrossRef: {e}")

    return papers
