import json
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class ClaimEvaluation:
    claim_text: str
    category: str  # Methodology, Diagnostic_Accuracy, Efficacy, Generalization
    empirical_support_score: int  # 1 a 10
    methodological_rigor_score: int  # 1 a 10
    statistical_validity_score: int  # 1 a 10
    risk_of_bias_score: int  # 1 a 10 (10 = menor viés)
    overall_confidence: float  # 0 a 100
    verdict: str  # STRONG_EVIDENCE, QUALIFIED_SUPPORT, WEAK_EVIDENCE, UNFOUNDED_OVERCLAIM
    supporting_evidence_excerpt: str
    counter_evidence_or_limitation: str
    judge_justification: str

@dataclass
class PaperJudgmentReport:
    paper_title: str
    overall_scientific_rigor: float  # 0 a 100
    evaluations: List[ClaimEvaluation]
    summary_verdict: str
    strengths: List[str]
    critical_flaws: List[str]
    recommended_reading_status: str  # ACCEPT_CORE, USE_WITH_CAVEATS, SKEPTICAL

class ArgumentJudgeAgent:
    """Agente IA as a Judge para auditoria e validação rigorosa de alegações científicas."""

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
            "temperature": 0.1,  # Baixa temperatura para julgamento estrito e determinístico
            "response_format": {"type": "json_object"}
        }
        
        try:
            res = requests.post(url, json=payload, headers=headers, timeout=120)
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            # Fallback para extração direta se JSON mode não for suportado pelo modelo
            payload.pop("response_format", None)
            res = requests.post(url, json=payload, headers=headers, timeout=120)
            res.raise_for_status()
            return res.json()["choices"][0]["message"]["content"]

    def judge_paper(self, paper_title: str, text_or_sections: Dict[str, str]) -> PaperJudgmentReport:
        """Avalia com rigor de juiz científico as alegações centrais de um artigo."""
        methods = text_or_sections.get("methods", "")[:4000]
        results = text_or_sections.get("results", "")[:4000]
        abstract = text_or_sections.get("abstract", "")[:2000]
        discussion = text_or_sections.get("discussion", "")[:2000]

        system_prompt = (
            "Você é um Juiz Científico de Elite (AI-as-a-Judge) para artigos de IA em Saúde e Medicina. "
            "Sua tarefa é auditar as alegações dos autores com ceticismo metodológico absoluto. "
            "Avalie se os resultados empíricos realmente sustentam as conclusões ou se há exagero (overclaiming). "
            "Responda estritamente em formato JSON com o seguinte esquema:\n"
            "{\n"
            "  'overall_scientific_rigor': 85,\n"
            "  'summary_verdict': 'QUALIFIED_SUPPORT',\n"
            "  'strengths': ['Validação externa em coorte independente', 'Métricas de calibração reportadas'],\n"
            "  'critical_flaws': ['Ausência de p-values em subgrupos', 'Possível vazamento de dados no pré-processamento'],\n"
            "  'recommended_reading_status': 'USE_WITH_CAVEATS',\n"
            "  'evaluations': [\n"
            "    {\n"
            "      'claim_text': 'O modelo supera médicos especialistas em sensibilidade',\n"
            "      'category': 'Diagnostic_Accuracy',\n"
            "      'empirical_support_score': 8,\n"
            "      'methodological_rigor_score': 7,\n"
            "      'statistical_validity_score': 6,\n"
            "      'risk_of_bias_score': 7,\n"
            "      'overall_confidence': 72.5,\n"
            "      'verdict': 'QUALIFIED_SUPPORT',\n"
            "      'supporting_evidence_excerpt': 'Tabela 2: Sensibilidade 94.2% vs 88.1%',\n"
            "      'counter_evidence_or_limitation': 'Amostra de teste continha apenas casos graves',\n"
            "      'judge_justification': 'Embora a métrica seja superior, a coorte não reflete a prevalência ambulatorial real.'\n"
            "    }\n"
            "  ]\n"
            "}"
        )

        user_prompt = (
            f"Artigo: {paper_title}\n\n"
            f"=== ABSTRACT ===\n{abstract}\n\n"
            f"=== MÉTODOS ===\n{methods}\n\n"
            f"=== RESULTADOS ===\n{results}\n\n"
            f"=== DISCUSSÃO ===\n{discussion}\n\n"
            "Conduza o julgamento estrito das alegações principais."
        )

        raw_response = self._call_llm(system_prompt, user_prompt)
        
        # Parse JSON
        try:
            # Limpeza caso venha envolvido em markdown ```json
            cleaned = raw_response.strip()
            if cleaned.startswith("```json"):
                cleaned = cleaned[7:]
            if cleaned.startswith("```"):
                cleaned = cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
        except Exception:
            data = {
                "overall_scientific_rigor": 50,
                "summary_verdict": "ANALYSIS_PARSING_FALLBACK",
                "strengths": ["Texto processado"],
                "critical_flaws": ["Erro na serialização do veredito"],
                "recommended_reading_status": "USE_WITH_CAVEATS",
                "evaluations": []
            }

        eval_objs = [ClaimEvaluation(**item) for item in data.get("evaluations", [])]
        
        return PaperJudgmentReport(
            paper_title=paper_title,
            overall_scientific_rigor=float(data.get("overall_scientific_rigor", 50.0)),
            evaluations=eval_objs,
            summary_verdict=data.get("summary_verdict", "INCONCLUSIVE"),
            strengths=data.get("strengths", []),
            critical_flaws=data.get("critical_flaws", []),
            recommended_reading_status=data.get("recommended_reading_status", "USE_WITH_CAVEATS")
        )
