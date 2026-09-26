"""Cliente LLM (ai-api, OpenAI-compatible) com a cadeia de 3 chamadas:

1. SOAP (titular gpt-oss:20b) com citações [mm:ss];
2. Laudo a partir da SOAP (mesmo titular);
3. Verificação cruzada barata (qwen3:8b) — divergências nos dois sentidos.

Backend `stub` (ESCUTA_LLM_BACKEND=stub) devolve respostas determinísticas
para desenvolvimento/testes sem GPU.
"""
from __future__ import annotations

import json
import re
import time
from typing import Any

import httpx

from .config import Settings
from .prompts import load_prompts


class LlmError(RuntimeError):
    pass


def _strip_fences(text: str) -> str:
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    return (m.group(1) if m else text).strip()


def parse_json_reply(text: str) -> dict[str, Any]:
    m = re.search(r"\{.*\}", _strip_fences(text), re.DOTALL)
    if not m:
        raise LlmError(f"resposta sem JSON: {text[:200]}")
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError as exc:
        raise LlmError(f"JSON inválido: {exc}: {text[:200]}") from exc


class HttpLlm:
    def __init__(self, settings: Settings) -> None:
        import httpx

        self._s = settings
        self._client = httpx.Client(timeout=1800.0)
        self._key = settings.env_secret(settings.llm_api_key_env)
        self._prompts = load_prompts(settings.prompts_dir)

    def chat(self, model: str, system: str, user: str, temperature: float = 0.3,
             max_tokens: int = 16384) -> str:
        """Modo nativo (URL .../api/chat): Ollama direto com think=false.

        Orçamento: 16384 por padrão (8x o máximo observado de raciocínio+SOAP;
        teto alto não interfere, mas limita pior caso a ~3 min/chamada).
        Modo OpenAI (URL /v1/chat/completions): 5xx (titular frio) com 1 retry,
        e content vazio (raciocínio consumiu o orçamento) com retry dobrando.
        """
        headers = {"Authorization": f"Bearer {self._key}"} if self._key else {}
        native = self._s.llm_url.rstrip("/").endswith("/api/chat")
        if native:
            # think=false acelera modelos que honram a flag (qwen3); se a resposta
            # vier vazia (modelo que ignora/estranha a flag), reintenta sem ela.
            for think in (False, None):
                payload = {
                    "model": model,
                    "messages": [{"role": "system", "content": system},
                                 {"role": "user", "content": user}],
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                }
                if think is not None:
                    payload["think"] = think
                resp = self._client.post(self._s.llm_url, json=payload, headers=headers)
                if resp.status_code >= 400:
                    raise LlmError(f"LLM {resp.status_code}: {resp.text[:300]}")
                data = resp.json()
                content = (data.get("message") or {}).get("content") or ""
                if content.strip():
                    return content
            raise LlmError(f"resposta vazia do modelo {model}: {str(data)[:200]}")

        content = ""
        for attempt in range(3):
            payload = {
                "model": model,
                "messages": [{"role": "system", "content": system},
                             {"role": "user", "content": user}],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            try:
                resp = self._client.post(self._s.llm_url, json=payload, headers=headers)
            except httpx.TimeoutException as exc:
                if attempt == 0:
                    time.sleep(20)
                    continue
                raise LlmError(f"timeout LLM: {exc}") from exc
            if resp.status_code >= 500 and attempt == 0:
                time.sleep(20)  # modelo carregando (frio) — reintenta
                continue
            if resp.status_code >= 400:
                raise LlmError(f"LLM {resp.status_code}: {resp.text[:300]}")
            data = resp.json()
            try:
                content = data["choices"][0]["message"]["content"] or ""
            except (KeyError, IndexError) as exc:
                raise LlmError(f"resposta inesperada: {str(data)[:200]}") from exc
            if content.strip():
                return content
            max_tokens *= 2  # thinking consumiu o orçamento; folga e repete
        return content

    # -- cadeia clínica ------------------------------------------------------

    def soap(self, dialogue: str) -> dict[str, Any]:
        from .prompts import SOAP_USER

        reply = self.chat(self._s.soap_model, self._prompts["soap_system"],
                          SOAP_USER.format(dialogue=dialogue), temperature=0.2)
        data = parse_json_reply(reply)
        for key in ("S", "O", "A", "P"):
            data.setdefault(key, "não informado")
        return data

    def laudo(self, soap: dict[str, Any]) -> str:
        from .prompts import LAUDO_USER

        soap_text = "\n".join(f"{k}: {v}" for k, v in soap.items() if k in "SOAP" and len(k) == 1)
        return self.chat(self._s.soap_model, self._prompts["laudo_system"],
                         LAUDO_USER.format(soap=soap_text or str(soap)), temperature=0.3)

    def verify(self, dialogue: str, soap: dict[str, Any]) -> dict[str, list[str]]:
        from .prompts import VERIFY_USER

        soap_text = json.dumps(soap, ensure_ascii=False)
        reply = self.chat(self._s.verify_model, self._prompts["verify_system"],
                          VERIFY_USER.format(dialogue=dialogue[:20000], soap=soap_text),
                          temperature=0.1, max_tokens=2048)
        data = parse_json_reply(reply)
        return {"sem_cobertura": list(data.get("sem_cobertura") or []),
                "sem_evidencia": list(data.get("sem_evidencia") or [])}

    def verify_roles(self, dialogue: str, speakers: list[str]) -> dict[str, str]:
        from .prompts import ROLES_USER

        reply = self.chat(self._s.verify_model, self._prompts["roles_system"],
                          ROLES_USER.format(dialogue=dialogue[:8000]), temperature=0.0, max_tokens=256)
        from .roles import parse_llm_roles_reply

        return parse_llm_roles_reply(reply, speakers)


class StubLlm:
    """Respostas determinísticas (dev/testes). Papéis alternados p/ divergência testável."""

    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._prompts = load_prompts(settings.prompts_dir)
        self.calls: list[str] = []

    def chat(self, model: str, system: str, user: str, **_: Any) -> str:
        self.calls.append(system[:40])
        return "stub"

    def soap(self, dialogue: str) -> dict[str, Any]:
        self.calls.append("soap")
        return {
            "S": "Paciente relata ardência ocular ao final do dia [00:02].",
            "O": "Exame com córnea pontilhada no terço inferior [00:31].",
            "A": "Ceratopatia por olho seco moderada [00:35].",
            "P": "Colírio lubrificante sem conservante, 1 gota 4x/dia [00:37].",
        }

    def laudo(self, soap: dict[str, Any]) -> str:
        self.calls.append("laudo")
        return ("IDENTIFICAÇÃO: não informado\nTÉCNICA: não informado\n"
                "DESCRIÇÃO: córnea com pontilhado no terço inferior.\n"
                "IMPRESSÃO DIAGNÓSTICA: ceratopatia por olho seco (CID-10 H16.2).\n"
                "CONDUTA: lubrificante sem conservante.\n"
                "Laudo gerado por IA (LAPAN). Revisado e assinado por: ____")

    def verify(self, dialogue: str, soap: dict[str, Any]) -> dict[str, list[str]]:
        self.calls.append("verify")
        return {"sem_cobertura": ["Alergia a dipirona citada e ausente na SOAP [00:41]"],
                "sem_evidencia": []}

    def verify_roles(self, dialogue: str, speakers: list[str]) -> dict[str, str]:
        self.calls.append("roles")
        if len(speakers) >= 2:
            return {speakers[0]: "MEDICO", speakers[1]: "PACIENTE"}
        return {speakers[0]: "MEDICO"} if speakers else {}


def make_llm(settings: Settings) -> Any:
    if settings.llm_backend == "http":
        return HttpLlm(settings)
    if settings.llm_backend == "stub":
        return StubLlm(settings)
    raise LlmError(f"backend LLM desconhecido: {settings.llm_backend}")
