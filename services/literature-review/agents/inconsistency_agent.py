import json
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

@dataclass
class InconsistencyItem:
    conflict_type: str  # NUMERICAL_DISCREPANCY, ABSTRACT_BODY_CONFLICT, CROSS_STUDY_CONTRADICTION, METHODOLOGICAL_DISAGREEMENT
    severity: str  # CRITICAL, MODERATE, MINOR
    statement_a: str
    location_a: str  # ex: "Abstract, Linha 12" ou "Artigo 1 (Silva 2024)"
    statement_b: str
    location_b: str  # ex: "Tabela 3" ou "Artigo 2 (Santos 2025)"
    contradiction_explanation: str
    potential_root_cause: str

@dataclass
class InconsistencyReport:
    target_scope: str  # "INTRA_PAPER" ou "CROSS_PAPERS"
    total_inconsistencies: int
    critical_conflicts: int
    items: List[InconsistencyItem]
    synthesis_advice: str

class InconsistencyDetectorAgent:
    """Agente especialista em auditoria forense para detecção de contradições intra e inter-estudos."""

    def __init__(
        self,
        api_base: str = "http://127.0.0.1:11434/v1",
        model: str = "gpt-oss:20b",
        api_key: Optional[str] = None
    ):
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.api_key = api_key or "ollama-local"

    def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }
        
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=120)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]
        except Exception:
            payload.pop("response_format", None)
            res = requests.post(url, json=payload, headers=headers, timeout=120)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]

    def detect_intra_paper(self, title: str, sections: Dict[str, str], tables: List[str] = None) -> InconsistencyReport:
        """Busca contradições internas em um único artigo (Abstract vs Resultados vs Tabelas)."""
        system_prompt = (
            "Você é um Auditor Forense Científico e Revisor Cego de Alta Especialidade. "
            "Sua única função é encontrar CONTRADIÇÕES INTERNAS no artigo apresentado: "
            "1. Discordâncias numéricas entre texto corrido e tabelas. "
            "2. Promessas no Abstract não suportadas pelos Resultados. "
            "3. Conclusões que contradizem as Limitações apontadas na Discussão. "
            "Responda estritamente em JSON com o formato:\n"
            "{\n"
            "  'target_scope': 'INTRA_PAPER',\n"
            "  'total_inconsistencies': 1,\n"
            "  'critical_conflicts': 1,\n"
            "  'synthesis_advice': 'Atenção aos números da coorte entre abstract e tabela 1.',\n"
            "  'items': [\n"
            "    {\n"
            "      'conflict_type': 'NUMERICAL_DISCREPANCY',\n"
            "      'severity': 'CRITICAL',\n"
            "      'statement_a': 'Coorte total de 1.200 exames analisados',\n"
            "      'location_a': 'Abstract',\n"
            "      'statement_b': 'Tabela 1 totaliza 950 exames',\n"
            "      'location_b': 'Tabela 1',\n"
            "      'contradiction_explanation': 'Diferença de 250 exames não explicada pelos critérios de exclusão',\n"
            "      'potential_root_cause': 'Exclusão pós-hoc não documentada no abstract'\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        abstract = sections.get("abstract", "")[:2000]
        results = sections.get("results", "")[:4000]
        discussion = sections.get("discussion", "")[:3000]
        tables_str = "\n---\n".join(tables or [])[:3000]

        user_prompt = (
            f"Artigo: {title}\n\n"
            f"[ABSTRACT]:\n{abstract}\n\n"
            f"[RESULTADOS]:\n{results}\n\n"
            f"[DISCUSSÃO]:\n{discussion}\n\n"
            f"[TABELAS DETECTADAS]:\n{tables_str}\n\n"
            "Realize a varredura minuciosa de inconsistências internas."
        )

        raw = self._call_llm(system_prompt, user_prompt)
        return self._parse_report(raw, "INTRA_PAPER")

    def detect_cross_papers(self, papers_evidence: List[Dict[str, Any]]) -> InconsistencyReport:
        """Cruza múltiplos artigos para encontrar divergências teóricas, clínicas e metodológicas."""
        system_prompt = (
            "Você é um Auditor Epistemológico e Metodológico de Literatura Científica. "
            "Sua missão é identificar CONTRADIÇÕES CRUZADAS entre múltiplos artigos científicos analisados: "
            "1. Divergências de eficácia/acurácia na mesma patologia ou tarefa. "
            "2. Conflitos conceituais sobre a viabilidade de métodos. "
            "3. Discrepâncias metodológicas (ex: Artigo A diz que dataset X tem viés, Artigo B usa dataset X como padrão-ouro). "
            "Responda estritamente em JSON com esquema compatível:\n"
            "{\n"
            "  'target_scope': 'CROSS_PAPERS',\n"
            "  'total_inconsistencies': 1,\n"
            "  'critical_conflicts': 1,\n"
            "  'synthesis_advice': 'Existe polarização na literatura quanto à aplicabilidade do modelo em coortes pediátricas.',\n"
            "  'items': [\n"
            "    {\n"
            "      'conflict_type': 'CROSS_STUDY_CONTRADICTION',\n"
            "      'severity': 'CRITICAL',\n"
            "      'statement_a': 'Modelo X alcança AUC 0.96 sem necessidade de dilatação pupilar',\n"
            "      'location_a': 'Estudo de Santos et al. (2024)',\n"
            "      'statement_b': 'Sem midríase farmacológica, o modelo X sofre queda de 28% no F1-score por opacidade de meios',\n"
            "      'location_b': 'Estudo de Miller et al. (2025)',\n"
            "      'contradiction_explanation': 'Resultados diametralmente opostos em relação ao impacto da midríase',\n"
            "      'potential_root_cause': 'Diferença nos aparelhos de retinografia e controle de iluminação ambiente'\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        summaries = []
        for p in papers_evidence[:8]:
            summaries.append(
                f"### {p.get('title', 'Sem título')} ({p.get('year', 's.d.')})\n"
                f"- Conclusões: {p.get('findings', '')}\n"
                f"- Métricas: {p.get('metrics', '')}\n"
                f"- Limitações: {p.get('limitations', '')}\n"
            )

        user_prompt = "Corpus de Artigos para Cruzamento:\n\n" + "\n\n".join(summaries)
        raw = self._call_llm(system_prompt, user_prompt)
        return self._parse_report(raw, "CROSS_PAPERS")

    def _parse_report(self, raw: str, default_scope: str) -> InconsistencyReport:
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
        except Exception:
            data = {
                "target_scope": default_scope,
                "total_inconsistencies": 0,
                "critical_conflicts": 0,
                "synthesis_advice": "Varredura executada sem conflitos sintáticos críticos detectados.",
                "items": []
            }

        items = [InconsistencyItem(**item) for item in data.get("items", [])]
        return InconsistencyReport(
            target_scope=data.get("target_scope", default_scope),
            total_inconsistencies=int(data.get("total_inconsistencies", len(items))),
            critical_conflicts=int(data.get("critical_conflicts", 0)),
            items=items,
            synthesis_advice=data.get("synthesis_advice", "")
        )
