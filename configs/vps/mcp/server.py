"""LAPAN MCP server — tools over the local AI stack for ChatGPT connectors.

Deployed on the VPS, calls LiteLLM internally (virtual key MCP_LITELLM_KEY,
budget-capped). Prototype auth model: unauthenticated FastMCP on a dedicated
route, protected by Traefik rate-limit; upgrade path = FastMCP OAuth
(oauth-proxy pattern) or IP allowlist of OpenAI egress ranges.
"""
import os

import httpx
from fastmcp import FastMCP

try:
    from mcp.types import ToolAnnotations

    _RO = ToolAnnotations(readOnlyHint=True)  # skips write-confirmation UX
except Exception:  # annotations are optional
    _RO = None

LITELLM_BASE = os.environ.get("LITELLM_BASE", "http://litellm:4000/v1")
LITELLM_KEY = os.environ["MCP_LITELLM_KEY"]
MODEL = os.environ.get("MCP_MODEL", "lapan")

mcp = FastMCP("LAPAN AI")


def _litellm_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {LITELLM_KEY}"}


@mcp.tool(annotations=_RO)
def listar_modelos() -> str:
    """Lista os modelos de IA disponíveis no servidor do LAPAN."""
    r = httpx.get(f"{LITELLM_BASE}/models", headers=_litellm_headers(), timeout=15)
    r.raise_for_status()
    ids = [m["id"] for m in r.json().get("data", [])]
    return ", ".join(sorted(ids)) if ids else "nenhum modelo disponível"


@mcp.tool(annotations=_RO)
def gerar_laudo(instrucao: str, achados: str, modelo: str = MODEL) -> str:
    """Gera um texto clínico (laudo/nota SOAP/extração) com o modelo local.

    Args:
        instrucao: o que produzir (ex.: "laudo oftalmológico estruturado",
            "nota SOAP", "extração em JSON com as chaves ...").
        achados: dados brutos, achados do exame ou transcrição da consulta.
        modelo: opcional, um dos retornados por listar_modelos (padrão lapan).
    """
    system = (
        "Você é o assistente clínico do LAPAN rodando em infraestrutura "
        "local (hospital). Português técnico. Use exclusivamente os dados "
        "fornecidos; não invente achados; se faltar informação, escreva "
        '"não informado". Termine com a linha: "Texto gerado por IA '
        '(LAPAN). Revisão humana obrigatória."'
    )
    body = {
        "model": modelo,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": f"INSTRUÇÃO: {instrucao}\n\nDADOS/ACHADOS:\n{achados}"},
        ],
        "max_tokens": 1500,
        "temperature": 0.3,
    }
    r = httpx.post(
        f"{LITELLM_BASE}/chat/completions",
        headers=_litellm_headers() | {"Content-Type": "application/json"},
        json=body,
        timeout=240,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


if __name__ == "__main__":
    # default HTTP path is /mcp (matches the Traefik PathPrefix rule)
    mcp.run(transport="http", host="0.0.0.0", port=8000)
