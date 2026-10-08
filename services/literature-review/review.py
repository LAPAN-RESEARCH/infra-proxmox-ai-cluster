#!/usr/bin/env python3
import os
import sys

# Garantir que o diretório atual do módulo está no path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import argparse
from typing import List, Dict, Any

# Import engines
from engines.base import Paper
from engines.pubmed import search_pubmed
from engines.arxiv import search_arxiv
from engines.semanticscholar import search_semantic_scholar
from engines.crossref import search_crossref
from engines.europepmc import search_europepmc

# Import exporters
from exporters.bibtex import export_bibtex
from exporters.markdown_report import generate_markdown_report
from exporters.zotero_writer import download_open_access_pdf, inject_to_zotero_cloud

# Import OCR & Evaluation Agents
from processors.ocr_processor import ScientificDocumentProcessor
from agents.judge_agent import ArgumentJudgeAgent
from agents.inconsistency_agent import InconsistencyDetectorAgent

def deduplicate_papers(papers: List[Paper]) -> List[Paper]:
    """Deduplica artigos por DOI normalizado e similaridade de título."""
    seen_dois = set()
    seen_titles = set()
    unique_papers: List[Paper] = []

    for p in papers:
        norm_doi = p.normalized_doi()
        norm_title = p.normalized_title()

        if norm_doi and norm_doi in seen_dois:
            continue
        if norm_title in seen_titles:
            continue

        if norm_doi:
            seen_dois.add(norm_doi)
        if norm_title:
            seen_titles.add(norm_title)

        unique_papers.append(p)

    return unique_papers

def run_review(
    query: str,
    engines: List[str],
    max_per_engine: int = 10,
    output_dir: str = "./review_results",
    download_pdfs: bool = False,
    run_ocr: bool = False,
    judge_arguments: bool = False,
    detect_inconsistencies: bool = False,
    local_zotero_path: str = None,
    llm_api_base: str = "http://127.0.0.1:11434/v1",
    llm_model: str = "gpt-oss:20b",
    zotero_collection: str = None,
    zotero_user_id: str = None,
    zotero_api_key: str = None
) -> Dict[str, Any]:
    os.makedirs(output_dir, exist_ok=True)
    all_papers: List[Paper] = []

    print(f"[*] Iniciando busca bibliográfica abrangente para: '{query}'")
    print(f"[*] Fontes selecionadas: {', '.join(engines)}")

    engine_map = {
        "pubmed": search_pubmed,
        "arxiv": search_arxiv,
        "semanticscholar": search_semantic_scholar,
        "crossref": search_crossref,
        "europepmc": search_europepmc
    }

    for engine_name in engines:
        func = engine_map.get(engine_name.lower())
        if not func:
            print(f"[!] Motor desconhecido: {engine_name}")
            continue

        print(f" -> Consultando {engine_name.upper()}...")
        results = func(query, max_results=max_per_engine)
        print(f"    Encontrados {len(results)} artigos em {engine_name.upper()}")
        all_papers.extend(results)

    unique_papers = deduplicate_papers(all_papers)
    print(f"[+] Total de artigos únicos consolidados: {len(unique_papers)} (de {len(all_papers)} brutos)")

    # 1. Gerar e salvar BibTeX
    bibtex_content = export_bibtex(unique_papers)
    bib_path = os.path.join(output_dir, "references.bib")
    with open(bib_path, "w", encoding="utf-8") as f:
        f.write(bibtex_content)
    print(f"[+] Arquivo BibTeX gerado: {bib_path}")

    # 2. Baixar PDFs Open Access se solicitado
    pdf_paths: List[str] = []
    if download_pdfs:
        pdf_dir = os.path.join(output_dir, "pdfs")
        print(f"[*] Baixando PDFs de acesso aberto para: {pdf_dir}...")
        for p in unique_papers:
            if p.pdf_url:
                saved = download_open_access_pdf(p, pdf_dir)
                if saved:
                    pdf_paths.append(saved)
        print(f"[+] Total de PDFs baixados com sucesso: {len(pdf_paths)}")

    # 3. Adicionar PDFs locais do Zotero se indicado
    if local_zotero_path and os.path.isdir(local_zotero_path):
        print(f"[*] Escaneando acervo local do Zotero em: {local_zotero_path}...")
        for root, _, files in os.walk(local_zotero_path):
            for file in files:
                if file.lower().endswith(".pdf"):
                    pdf_paths.append(os.path.join(root, file))
        print(f"[+] Total de PDFs do Zotero adicionados à fila de processamento: {len(pdf_paths)}")

    # 4. Processamento Completo de Texto e OCR inteligente
    processed_docs = []
    if run_ocr and pdf_paths:
        print(f"[*] Processando {len(pdf_paths)} PDFs com OCR e segmentação estruturada...")
        processor = ScientificDocumentProcessor(cache_dir=os.path.join(output_dir, ".ocr_cache"))
        for p_path in pdf_paths[:15]:  # Processa os primeiros artigos prioritários
            try:
                doc = processor.process_pdf(p_path)
                processed_docs.append(doc)
                print(f"    [OCR] '{doc.title[:40]}...' ({doc.total_pages} págs, OCR={doc.ocr_applied})")
            except Exception as e:
                print(f"    [!] Erro ao processar PDF {p_path}: {e}")

    # 5. Agente IA as a Judge (Avaliação de Argumentos)
    judgment_reports = []
    if judge_arguments and processed_docs:
        print(f"[*] Executando IA as a Judge com modelo '{llm_model}' em {len(processed_docs)} documentos...")
        judge = ArgumentJudgeAgent(api_base=llm_api_base, model=llm_model)
        for doc in processed_docs:
            try:
                report = judge.judge_paper(doc.title, doc.sections)
                judgment_reports.append(report)
                print(f"    [Judge] '{doc.title[:30]}...' -> Rigor: {report.overall_scientific_rigor}/100 | Veredito: {report.summary_verdict}")
            except Exception as e:
                print(f"    [!] Falha no julgamento de '{doc.title}': {e}")

    # 6. Agente Detector de Inconsistências
    inconsistency_reports = []
    if detect_inconsistencies and processed_docs:
        print(f"[*] Executando Agente Detector de Inconsistências...")
        detector = InconsistencyDetectorAgent(api_base=llm_api_base, model=llm_model)
        
        # Auditoria intra-artigo
        for doc in processed_docs:
            try:
                intra_rep = detector.detect_intra_paper(doc.title, doc.sections, doc.tables)
                if intra_rep.total_inconsistencies > 0:
                    inconsistency_reports.append(intra_rep)
                    print(f"    [Inconsistência] '{doc.title[:30]}...' -> {intra_rep.total_inconsistencies} conflito(s) interno(s)!")
            except Exception as e:
                print(f"    [!] Erro na detecção interna: {e}")

        # Auditoria cruzada entre estudos
        cross_evidence = []
        for doc in processed_docs:
            cross_evidence.append({
                "title": doc.title,
                "findings": doc.sections.get("results", "")[:1000],
                "limitations": doc.sections.get("discussion", "")[:1000],
                "metrics": ", ".join(doc.tables[:2]) if doc.tables else "Não tabuladas"
            })
        if len(cross_evidence) >= 2:
            try:
                cross_rep = detector.detect_cross_papers(cross_evidence)
                inconsistency_reports.append(cross_rep)
                print(f"    [Inconsistência Cruzada] Encontradas {cross_rep.total_inconsistencies} divergências entre estudos!")
            except Exception as e:
                print(f"    [!] Erro na detecção cruzada: {e}")

    # 7. Gerar e salvar Relatório Markdown Enriquecido
    base_md = generate_markdown_report(query, unique_papers)
    full_report_lines = [base_md, ""]

    if judgment_reports:
        full_report_lines.append("## ⚖️ Julgamento Científico de Argumentos (IA as a Judge)")
        full_report_lines.append("")
        for j in judgment_reports:
            full_report_lines.append(f"### Artigo: {j.paper_title}")
            full_report_lines.append(f"- **Rigor Científico Global:** `{j.overall_scientific_rigor}/100`")
            full_report_lines.append(f"- **Veredito do Juiz:** **{j.summary_verdict}** (Recomendação: `{j.recommended_reading_status}`)")
            if j.strengths:
                full_report_lines.append(f"- **Pontos Fortes:** {', '.join(j.strengths)}")
            if j.critical_flaws:
                full_report_lines.append(f"- **Falhas Críticas / Ressalvas:** {', '.join(j.critical_flaws)}")
            
            full_report_lines.append("")
            full_report_lines.append("#### Auditoria de Alegações:")
            for ev in j.evaluations:
                full_report_lines.append(f"  * **Alegação:** *\"{ev.claim_text}\"*")
                full_report_lines.append(f"    - Categoria: `{ev.category}` | Veredito: **{ev.verdict}** (Confiança: {ev.overall_confidence}%)")
                full_report_lines.append(f"    - Suporte Empírico: {ev.empirical_support_score}/10 | Rigor: {ev.methodological_rigor_score}/10 | Estatística: {ev.statistical_validity_score}/10")
                full_report_lines.append(f"    - Evidência: `{ev.supporting_evidence_excerpt}`")
                full_report_lines.append(f"    - Justificativa do Juiz: {ev.judge_justification}")
            full_report_lines.append("")

    if inconsistency_reports:
        full_report_lines.append("## 🔍 Relatório Forense de Inconsistências & Contradições")
        full_report_lines.append("")
        for rep in inconsistency_reports:
            scope_label = "Contradições Internas no Artigo" if rep.target_scope == "INTRA_PAPER" else "Divergências Cruzadas entre Artigos"
            full_report_lines.append(f"### {scope_label} (Conflitos Críticos: {rep.critical_conflicts})")
            if rep.synthesis_advice:
                full_report_lines.append(f"> **Parecer Forense:** {rep.synthesis_advice}")
                full_report_lines.append("")
            for it in rep.items:
                full_report_lines.append(f"- **Tipo:** `{it.conflict_type}` [{it.severity}]")
                full_report_lines.append(f"  * Posição A ({it.location_a}): *\"{it.statement_a}\"*")
                full_report_lines.append(f"  * Posição B ({it.location_b}): *\"{it.statement_b}\"*")
                full_report_lines.append(f"  * **Análise da Contradição:** {it.contradiction_explanation}")
                if it.potential_root_cause:
                    full_report_lines.append(f"  * **Causa Raiz Provável:** {it.potential_root_cause}")
            full_report_lines.append("")

    md_path = os.path.join(output_dir, "literature_review_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(full_report_lines))
    print(f"[+] Relatório completo enriquecido salvo em: {md_path}")

    # 8. Injetar no Zotero se credenciais forem fornecidas
    zotero_injected = 0
    if zotero_collection and zotero_user_id and zotero_api_key:
        print(f"[*] Injetando referências na coleção '{zotero_collection}' do Zotero...")
        zotero_injected = inject_to_zotero_cloud(
            unique_papers,
            library_id=zotero_user_id,
            api_key=zotero_api_key,
            collection_name=zotero_collection
        )
        print(f"[+] Artigos criados no Zotero: {zotero_injected}")

    return {
        "total_unique": len(unique_papers),
        "bibtex_path": bib_path,
        "report_path": md_path,
        "processed_docs_ocr": len(processed_docs),
        "judgments": len(judgment_reports),
        "inconsistencies": len(inconsistency_reports),
        "zotero_injected": zotero_injected
    }

def main():
    parser = argparse.ArgumentParser(description="Revisão Bibliográfica Multi-Site Automatizada com OCR, IA-as-a-Judge e Detecção de Inconsistências")
    parser.add_argument("--query", "-q", required=True, help="Pergunta de pesquisa ou termos-chave")
    parser.add_argument("--max-per-engine", "-m", type=int, default=10, help="Máximo de artigos por motor")
    parser.add_argument("--engines", "-e", default="pubmed,arxiv,semanticscholar,crossref,europepmc",
                        help="Motores separados por vírgula (pubmed,arxiv,semanticscholar,crossref,europepmc)")
    parser.add_argument("--output-dir", "-o", default="./review_results", help="Diretório de saída")
    parser.add_argument("--download-pdfs", action="store_true", help="Baixar PDFs de acesso aberto disponíveis")
    parser.add_argument("--full-text-ocr", action="store_true", help="Executar OCR e extração estruturada completa dos PDFs")
    parser.add_argument("--judge-arguments", action="store_true", help="Ativar IA as a Judge para auditoria científica de alegações")
    parser.add_argument("--detect-inconsistencies", action="store_true", help="Ativar Agente Detector de Inconsistências e Contradições")
    parser.add_argument("--local-zotero-path", default=None, help="Caminho da pasta storage do Zotero com PDFs locais")
    parser.add_argument("--llm-api-base", default=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434/v1"), help="URL base da API do LLM")
    parser.add_argument("--llm-model", default="gpt-oss:20b", help="Modelo de IA utilizado pelos agentes avaliadores")
    parser.add_argument("--zotero-collection", help="Nome da coleção no Zotero para salvar os itens")
    parser.add_argument("--zotero-user-id", default=os.getenv("ZOTERO_USER_ID"), help="User ID da conta Zotero")
    parser.add_argument("--zotero-api-key", default=os.getenv("ZOTERO_API_KEY"), help="API Key da conta Zotero")

    args = parser.parse_args()
    engine_list = [e.strip() for e in args.engines.split(",") if e.strip()]

    run_review(
        query=args.query,
        engines=engine_list,
        max_per_engine=args.max_per_engine,
        output_dir=args.output_dir,
        download_pdfs=args.download_pdfs,
        run_ocr=args.full_text_ocr,
        judge_arguments=args.judge_arguments,
        detect_inconsistencies=args.detect_inconsistencies,
        local_zotero_path=args.local_zotero_path,
        llm_api_base=args.llm_api_base,
        llm_model=args.llm_model,
        zotero_collection=args.zotero_collection,
        zotero_user_id=args.zotero_user_id,
        zotero_api_key=args.zotero_api_key
    )

if __name__ == "__main__":
    main()
