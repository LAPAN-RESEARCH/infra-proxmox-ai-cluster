#!/usr/bin/env python3
"""
Utilitário de consulta ao Zotero e Leitura de PDFs com OCR para o Agente OpenClaw.
"""
import argparse
import json
import os
import sqlite3
import subprocess
import sys

DB_PATH = os.environ.get("ZOTERO_DB_PATH", "/home/node/Zotero/zotero.sqlite")
STORAGE_DIR = os.environ.get("ZOTERO_STORAGE_DIR", "/home/node/Zotero/storage")

def get_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Banco do Zotero não encontrado em: {DB_PATH}")
    return sqlite3.connect(f"file:{DB_PATH}?immutable=1", uri=True)

def search_items(query: str, limit: int = 15):
    conn = get_connection()
    c = conn.cursor()
    search_term = f"%{query}%"
    c.execute("""
        SELECT DISTINCT
            p.itemID,
            p.key as item_key,
            idv_title.value as title,
            idv_abs.value as abstract,
            att.key as attachment_key
        FROM items p
        JOIN itemData id_t ON p.itemID = id_t.itemID
        JOIN fields f_t ON id_t.fieldID = f_t.fieldID AND f_t.fieldName = 'title'
        JOIN itemDataValues idv_title ON id_t.valueID = idv_title.valueID
        LEFT JOIN itemData id_a ON p.itemID = id_a.itemID
        LEFT JOIN fields f_a ON id_a.fieldID = f_a.fieldID AND f_a.fieldName = 'abstractNote'
        LEFT JOIN itemDataValues idv_abs ON id_a.valueID = idv_abs.valueID
        LEFT JOIN itemAttachments ia ON p.itemID = ia.parentItemID AND ia.contentType = 'application/pdf'
        LEFT JOIN items att ON ia.itemID = att.itemID
        WHERE (idv_title.value LIKE ? OR (idv_abs.value IS NOT NULL AND idv_abs.value LIKE ?))
        LIMIT ?
    """, (search_term, search_term, limit))
    
    results = []
    for row in c.fetchall():
        item_id, item_key, title, abstract, att_key = row
        pdf_full_path = None
        if att_key:
            folder = os.path.join(STORAGE_DIR, att_key)
            if os.path.isdir(folder):
                for f in os.listdir(folder):
                    if f.lower().endswith(".pdf"):
                        pdf_full_path = os.path.join(folder, f)
                        break
        
        results.append({
            "item_id": item_id,
            "key": item_key,
            "title": title,
            "abstract": (abstract[:300] + "...") if abstract and len(abstract) > 300 else abstract,
            "pdf_path": pdf_full_path,
            "has_pdf": pdf_full_path is not None
        })
    return results

def read_pdf(pdf_path: str, max_pages: int = 15, ocr_fallback: bool = True):
    if not os.path.isfile(pdf_path):
        return {"error": f"Arquivo não encontrado: {pdf_path}"}
    
    try:
        import pymupdf
    except ImportError:
        import fitz as pymupdf
        
    doc = pymupdf.open(pdf_path)
    pages_text = []
    
    for i in range(min(len(doc), max_pages)):
        text = doc[i].get_text()
        # Se página tiver pouquíssimo texto, pode ser página escaneada
        if len(text.strip()) < 80 and ocr_fallback:
            pix = doc[i].get_pixmap(dpi=200)
            tmp_img = f"/tmp/zotero_ocr_page_{i}_{os.getpid()}.png"
            pix.save(tmp_img)
            try:
                ocr_out = subprocess.check_output(
                    ["tesseract", tmp_img, "stdout", "-l", "eng+por", "--psm", "1"],
                    text=True, stderr=subprocess.DEVNULL
                )
                if len(ocr_out.strip()) > 30:
                    text = f"[OCR Tesseract Page {i+1}]:\n{ocr_out.strip()}"
            except Exception:
                pass
            finally:
                if os.path.exists(tmp_img):
                    os.remove(tmp_img)
                    
        pages_text.append({
            "page": i + 1,
            "text": text.strip()
        })
        
    return {
        "pdf_path": pdf_path,
        "total_pages": len(doc),
        "pages_read": len(pages_text),
        "content": pages_text
    }

def main():
    parser = argparse.ArgumentParser(description="Zotero Search & PDF OCR tool for OpenClaw Agent")
    subparsers = parser.add_subparsers(dest="command")
    
    search_p = subparsers.add_parser("search", help="Buscar itens no Zotero por palavra-chave")
    search_p.add_argument("query", help="Termo de pesquisa (título ou resumo)")
    search_p.add_argument("--limit", type=int, default=10, help="Número máximo de itens")
    search_p.add_argument("--json", action="store_true", help="Retornar em formato JSON")
    
    read_p = subparsers.add_parser("read-pdf", help="Ler e extrair texto de um PDF (com OCR se necessário)")
    read_p.add_argument("path", help="Caminho completo do PDF no storage")
    read_p.add_argument("--max-pages", type=int, default=15, help="Número de páginas para ler")
    read_p.add_argument("--json", action="store_true", help="Retornar em formato JSON")

    args = parser.parse_args()
    if args.command == "search":
        res = search_items(args.query, limit=args.limit)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"Encontrados {len(res)} itens para: '{args.query}'\n")
            for r in res:
                badge = "[PDF DISPONÍVEL]" if r["has_pdf"] else "[SEM PDF]"
                print(f"ID {r['item_id']} | {badge} | {r['title']}")
                if r["has_pdf"]:
                    print(f"  -> PDF: {r['pdf_path']}")
                if r["abstract"]:
                    print(f"  -> Resumo: {r['abstract']}")
                print("-" * 60)
    elif args.command == "read-pdf":
        res = read_pdf(args.path, max_pages=args.max_pages)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"Arquivo: {res.get('pdf_path')} (Páginas lidas: {res.get('pages_read')}/{res.get('total_pages')})\n")
            for p in res.get("content", []):
                print(f"=== Página {p['page']} ===")
                print(p["text"])
                print()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
