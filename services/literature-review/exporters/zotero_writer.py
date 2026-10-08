import os
import requests
from typing import List, Optional

try:
    from engines.base import Paper
except (ImportError, ValueError):
    from ..engines.base import Paper


def download_open_access_pdf(paper: Paper, target_dir: str) -> Optional[str]:
    """Baixa o PDF de acesso aberto (se disponível) para o diretório de destino."""
    if not paper.pdf_url:
        return None

    os.makedirs(target_dir, exist_ok=True)
    safe_name = "".join(c for c in paper.title[:50] if c.isalnum() or c in (' ', '_', '-')).rstrip()
    filename = f"{paper.year or 'nd'}_{safe_name}.pdf"
    file_path = os.path.join(target_dir, filename)

    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; LAPAN-Research/1.0)"}
        res = requests.get(paper.pdf_url, headers=headers, timeout=25, stream=True)
        if res.status_code == 200 and "application/pdf" in res.headers.get("Content-Type", ""):
            with open(file_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=8192):
                    f.write(chunk)
            return file_path
    except Exception as e:
        print(f"[Aviso] Não foi possível baixar PDF para '{paper.title[:30]}...': {e}")

    return None

def inject_to_zotero_cloud(papers: List[Paper], library_id: str, api_key: str, collection_name: str = "Revisao_Bibliografica") -> int:
    """Insere os artigos diretamente na conta Zotero via pyzotero."""
    try:
        from pyzotero import zotero
    except ImportError:
        print("[!] pyzotero não está instalado no ambiente Python atual.")
        return 0

    zot = zotero.Zotero(library_id, 'user', api_key)
    
    # 1. Obter ou criar coleção
    collections = zot.collections()
    col_key = None
    for col in collections:
        if col.get("data", {}).get("name") == collection_name:
            col_key = col.get("key")
            break

    if not col_key:
        new_col = zot.create_collections([{"name": collection_name}])
        if new_col and "successful" in new_col and new_col["successful"]:
            col_key = new_col["successful"]["0"]["key"]

    success_count = 0
    items_to_create = []

    for paper in papers:
        template = zot.item_template('journalArticle')
        template['title'] = paper.title
        template['abstractNote'] = paper.abstract or paper.tldr or ""
        template['publicationTitle'] = paper.journal or ""
        template['date'] = str(paper.year) if paper.year else ""
        template['DOI'] = paper.doi or ""
        template['url'] = paper.url or ""
        if col_key:
            template['collections'] = [col_key]

        creators = []
        for author in paper.authors:
            parts = author.strip().split()
            if len(parts) > 1:
                creators.append({
                    "creatorType": "author",
                    "firstName": " ".join(parts[:-1]),
                    "lastName": parts[-1]
                })
            else:
                creators.append({
                    "creatorType": "author",
                    "name": author
                })
        template['creators'] = creators
        items_to_create.append(template)

    if items_to_create:
        resp = zot.create_items(items_to_create)
        success_count = len(resp.get("successful", {}))

    return success_count
