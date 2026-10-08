import os
import re
import hashlib
import subprocess
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

try:
    import pymupdf  # PyMuPDF
except ImportError:
    try:
        import fitz as pymupdf
    except ImportError:
        pymupdf = None

@dataclass
class DocumentSection:
    heading: str
    content: str
    page_numbers: List[int] = field(default_factory=list)

@dataclass
class ProcessedDocument:
    file_path: str
    title: str
    total_pages: int
    scanned_pages: int
    digital_pages: int
    full_text: str
    sections: Dict[str, str] = field(default_factory=dict)
    tables: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    char_count: int = 0
    ocr_applied: bool = False

class ScientificDocumentProcessor:
    """Processador de PDFs científicos com extração estruturada e OCR inteligente com fallback."""

    def __init__(self, cache_dir: str = "/tmp/lapan_ocr_cache", ocr_lang: str = "eng+por"):
        self.cache_dir = cache_dir
        self.ocr_lang = ocr_lang
        os.makedirs(self.cache_dir, exist_ok=True)

    def _file_hash(self, path: str) -> str:
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _ocr_page_image(self, pixmap) -> str:
        """Executa Tesseract OCR em uma imagem de página renderizada."""
        img_path = os.path.join(self.cache_dir, f"temp_{os.getpid()}.png")
        txt_base = os.path.join(self.cache_dir, f"temp_{os.getpid()}")
        pixmap.save(img_path)
        try:
            cmd = [
                "tesseract",
                img_path,
                txt_base,
                "-l", self.ocr_lang,
                "--oem", "1",
                "--psm", "3"
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            txt_path = txt_base + ".txt"
            if os.path.exists(txt_path):
                with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                    text = f.read()
                os.remove(txt_path)
                return text
        except Exception as e:
            return f"[Erro no OCR: {e}]"
        finally:
            if os.path.exists(img_path):
                os.remove(img_path)
        return ""

    def process_pdf(self, pdf_path: str, force_ocr: bool = False) -> ProcessedDocument:
        if not os.path.isfile(pdf_path):
            raise FileNotFoundError(f"Arquivo PDF não encontrado: {pdf_path}")

        if pymupdf is None:
            raise RuntimeError("Biblioteca PyMuPDF (fitz) não está instalada no ambiente.")

        doc = pymupdf.open(pdf_path)
        total_pages = len(doc)
        pages_text: List[str] = []
        scanned_count = 0
        digital_count = 0
        ocr_applied = False

        for page_idx in range(total_pages):
            page = doc[page_idx]
            extracted = page.get_text("text").strip()

            # Heurística: se a página tiver menos de 100 caracteres, trata-se de scan ou imagem
            if len(extracted) < 100 or force_ocr:
                scanned_count += 1
                ocr_applied = True
                # Renderiza a página em 300 DPI (zoom 4.16x para escala de 72 DPI base)
                mat = pymupdf.Matrix(3.0, 3.0)
                pix = page.get_pixmap(matrix=mat)
                ocr_text = self._ocr_page_image(pix)
                pages_text.append(ocr_text if len(ocr_text) > len(extracted) else extracted)
            else:
                digital_count += 1
                pages_text.append(extracted)

        full_text = "\n\n".join(pages_text)
        sections = self._segment_sections(full_text)
        tables = self._extract_tables(full_text)

        meta = doc.metadata or {}
        title = meta.get("title") or self._heuristic_title(full_text, os.path.basename(pdf_path))

        doc.close()

        return ProcessedDocument(
            file_path=pdf_path,
            title=title,
            total_pages=total_pages,
            scanned_pages=scanned_count,
            digital_pages=digital_count,
            full_text=full_text,
            sections=sections,
            tables=tables,
            metadata=meta,
            char_count=len(full_text),
            ocr_applied=ocr_applied
        )

    def _heuristic_title(self, text: str, fallback: str) -> str:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        for line in lines[:8]:
            if len(line) > 15 and not line.lower().startswith(("http", "doi", "volume", "journal", "issn", "page")):
                return line
        return fallback.replace(".pdf", "").replace("_", " ")

    def _segment_sections(self, text: str) -> Dict[str, str]:
        """Segmenta o texto científico em seções padrão (Abstract, Methods, Results, etc.)."""
        patterns = {
            "abstract": r"(?i)\b(?:abstract|resumo)\b",
            "introduction": r"(?i)\b(?:1\.?\s*)?(?:introduction|introdução|background)\b",
            "methods": r"(?i)\b(?:2\.?\s*)?(?:methods|methodology|materials and methods|métodos|materiais e métodos)\b",
            "results": r"(?i)\b(?:3\.?\s*)?(?:results|findings|resultados)\b",
            "discussion": r"(?i)\b(?:4\.?\s*)?(?:discussion|discussão)\b",
            "conclusion": r"(?i)\b(?:5\.?\s*)?(?:conclusion|conclusão|conclusions)\b",
            "references": r"(?i)\b(?:references|bibliography|referências)\b"
        }

        indices = []
        for sec_name, pat in patterns.items():
            for m in re.finditer(pat, text):
                indices.append((m.start(), sec_name))
                break

        indices.sort(key=lambda x: x[0])
        sections = {}

        for i, (start_idx, sec_name) in enumerate(indices):
            end_idx = indices[i + 1][0] if i + 1 < len(indices) else len(text)
            sec_body = text[start_idx:end_idx].strip()
            # Remove o título da seção do início
            lines = sec_body.split("\n", 1)
            content = lines[1].strip() if len(lines) > 1 else sec_body
            sections[sec_name] = content

        return sections

    def _extract_tables(self, text: str) -> List[str]:
        """Detecta tabelas no texto através de cabeçalhos Table/Tabela."""
        table_blocks = []
        pattern = re.compile(r'(?i)(?:table|tabela)\s+\d+[:\.\-][^\n]+(?:\n[^\n]+){2,15}')
        for match in pattern.finditer(text):
            table_blocks.append(match.group(0).strip())
        return table_blocks
