import requests
import xml.etree.ElementTree as ET
from typing import List
from .base import Paper

def search_arxiv(query: str, max_results: int = 15) -> List[Paper]:
    """Busca no arXiv via API pública (Atom XML)."""
    base_url = "http://export.arxiv.org/api/query"
    papers: List[Paper] = []

    try:
        res = requests.get(
            base_url,
            params={
                "search_query": f"all:{query}",
                "start": 0,
                "max_results": max_results,
                "sortBy": "relevance",
                "sortOrder": "descending"
            },
            timeout=15
        )
        res.raise_for_status()

        root = ET.fromstring(res.content)
        ns = {"atom": "http://www.w3.org/2005/Atom", "arxiv": "http://arxiv.org/schemas/atom"}

        for entry in root.findall("atom:entry", ns):
            title = entry.findtext("atom:title", default="", namespaces=ns).strip().replace("\n", " ")
            summary = entry.findtext("atom:summary", default="", namespaces=ns).strip().replace("\n", " ")
            published = entry.findtext("atom:published", default="", namespaces=ns)
            year = int(published[:4]) if published and len(published) >= 4 else None

            authors = [
                author.findtext("atom:name", default="", namespaces=ns)
                for author in entry.findall("atom:author", ns)
            ]

            doi = entry.findtext("arxiv:doi", default=None, namespaces=ns)
            id_url = entry.findtext("atom:id", default="", namespaces=ns)

            pdf_url = None
            for link in entry.findall("atom:link", ns):
                if link.attrib.get("title") == "pdf" or link.attrib.get("type") == "application/pdf":
                    pdf_url = link.attrib.get("href")
                    break
            
            if not pdf_url and id_url:
                pdf_url = id_url.replace("/abs/", "/pdf/") + ".pdf"

            papers.append(Paper(
                title=title,
                authors=authors,
                abstract=summary,
                year=year,
                doi=doi,
                source="arxiv",
                url=id_url,
                pdf_url=pdf_url,
                journal="arXiv Preprint",
                extra={"arxiv_id": id_url.split("/")[-1]}
            ))
    except Exception as e:
        print(f"[Aviso] Falha na busca arXiv: {e}")

    return papers
