from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Paper:
    title: str
    authors: List[str] = field(default_factory=list)
    abstract: str = ""
    year: Optional[int] = None
    doi: Optional[str] = None
    source: str = ""  # pubmed, arxiv, semanticscholar, crossref, europepmc
    url: str = ""
    pdf_url: Optional[str] = None
    journal: str = ""
    citation_count: Optional[int] = None
    tldr: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def normalized_doi(self) -> Optional[str]:
        if not self.doi:
            return None
        doi = self.doi.strip().lower()
        if doi.startswith("https://doi.org/"):
            doi = doi[len("https://doi.org/"):]
        elif doi.startswith("http://doi.org/"):
            doi = doi[len("http://doi.org/"):]
        elif doi.startswith("doi:"):
            doi = doi[len("doi:"):].strip()
        return doi

    def normalized_title(self) -> str:
        import re
        clean = re.sub(r'[^a-zA-Z0-9\s]', '', self.title.lower())
        return " ".join(clean.split())
