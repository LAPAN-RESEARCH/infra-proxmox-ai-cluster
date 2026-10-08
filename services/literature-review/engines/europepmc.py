import requests
from typing import List
from .base import Paper

def search_europepmc(query: str, max_results: int = 15) -> List[Paper]:
    """Busca no Europe PMC para literatura biomédica, clínica e preprints (bioRxiv/medRxiv)."""
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    papers: List[Paper] = []

    try:
        res = requests.get(
            base_url,
            params={
                "query": query,
                "pageSize": max_results,
                "format": "json",
                "resultType": "core"
            },
            timeout=15
        )
        res.raise_for_status()
        result_list = res.json().get("resultList", {}).get("result", [])

        for item in result_list:
            title = item.get("title", "").strip().rstrip(".")
            author_str = item.get("authorString", "")
            authors = [a.strip() for a in author_str.split(",") if a.strip()]

            abstract = item.get("abstractText", "")
            pub_year = item.get("pubYear")
            year = int(pub_year) if pub_year and pub_year.isdigit() else None
            doi = item.get("doi")
            pmid = item.get("pmid")
            pmcid = item.get("pmcid")
            
            url = f"https://europepmc.org/article/MED/{pmid}" if pmid else f"https://doi.org/{doi}" if doi else ""
            
            pdf_url = None
            if item.get("isOpenAccess") == "Y" and pmcid:
                pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"

            journal_title = item.get("journalTitle") or item.get("journalInfo", {}).get("journal", {}).get("title", "")

            papers.append(Paper(
                title=title,
                authors=authors,
                abstract=abstract,
                year=year,
                doi=doi,
                source="europepmc",
                url=url,
                pdf_url=pdf_url,
                journal=journal_title,
                citation_count=item.get("citedByCount"),
                extra={"pmcid": pmcid, "pmid": pmid}
            ))
    except Exception as e:
        print(f"[Aviso] Falha na busca Europe PMC: {e}")

    return papers
