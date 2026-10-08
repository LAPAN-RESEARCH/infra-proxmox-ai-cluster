import requests
import xml.etree.ElementTree as ET
from typing import List
from .base import Paper

def search_pubmed(query: str, max_results: int = 15) -> List[Paper]:
    """Busca no PubMed via E-utilities (esearch + esummary/efetch)."""
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    papers: List[Paper] = []

    try:
        # 1. ESearch para obter IDs
        search_res = requests.get(
            f"{base_url}/esearch.fcgi",
            params={
                "db": "pubmed",
                "term": query,
                "retmax": max_results,
                "retmode": "json",
                "sort": "pub_date"
            },
            timeout=15
        )
        search_res.raise_for_status()
        id_list = search_res.json().get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return papers

        # 2. ESummary para metadados
        summary_res = requests.get(
            f"{base_url}/esummary.fcgi",
            params={
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json"
            },
            timeout=15
        )
        summary_res.raise_for_status()
        result_dict = summary_res.json().get("result", {})

        for pmid in id_list:
            doc = result_dict.get(pmid)
            if not doc:
                continue

            title = doc.get("title", "").strip().rstrip(".")
            authors = [a.get("name", "") for a in doc.get("authors", []) if "name" in a]
            pubdate = doc.get("pubdate", "")
            year = None
            for token in pubdate.split():
                if token.isdigit() and len(token) == 4:
                    year = int(token)
                    break

            doi = None
            for article_id in doc.get("articleids", []):
                if article_id.get("idtype") == "doi":
                    doi = article_id.get("value")
                    break

            source_journal = doc.get("source", "")
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

            papers.append(Paper(
                title=title,
                authors=authors,
                year=year,
                doi=doi,
                source="pubmed",
                url=url,
                journal=source_journal,
                extra={"pmid": pmid}
            ))
    except Exception as e:
        print(f"[Aviso] Falha na busca PubMed: {e}")

    return papers
