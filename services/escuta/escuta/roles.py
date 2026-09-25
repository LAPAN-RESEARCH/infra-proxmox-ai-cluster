"""Atribuição dos papéis MEDICO/PACIENTE (Pilar 3, decisão 2026-09-24).

Três fontes independentes; divergência => confirmação manual obrigatória:

1. enrollment ECAPA (embeddings de voz do médico) — `speakers.py`;
2. heurística semântica dos turnos (padrão interrogativo/prescritivo);
3. verificação semântica por LLM barato (qwen3:8b) — `llm.verify_roles`.

Este módulo é lógica pura (sem rede, sem GPU) e roda sobre o transcript
diarizado já alinhado.
"""
from __future__ import annotations

import re
from typing import Any, Callable

QUESTION_WORDS = (
    "qual", "quais", "quando", "onde", "como", "por que", "porque", "quanto tempo",
    "quantos", "quantas", "já usou", "tem alergia", "o que está sentindo", "desde quando",
)
DOCTOR_MARKERS = (
    "vou prescrever", "vou examinar", "vamos tratar", "volte", "retorno em", "reavalia",
    "conduta", "prescrição", "receita", "anotei", "vou fazer", "realizar", "solicitar",
    "uma gota", "comprimido", "colírio", "dosagem", "resultado do exame", "diagnóstico",
)
PATIENT_MARKERS = (
    "doutor", "doutora", "é grave", "preciso operar", "estou sentindo", "sinto",
    "me dói", "obrigad", "pode ser", "acho que",
)


def _count_markers(text: str, markers: tuple[str, ...]) -> int:
    low = text.lower()
    return sum(low.count(m) for m in markers)


def heuristic_scores(segments: list[dict[str, Any]]) -> dict[str, float]:
    """Score por falante: perguntas + vocabulário clínico dirigido.

    O médico pergunta, conduz a anamnese e prescreve; o paciente responde,
    relata sintomas na primeira pessoa e trata o interlocutor de doutor.
    """
    scores: dict[str, dict[str, float]] = {}
    for seg in segments:
        sp = seg.get("speaker")
        if not sp:
            continue
        text = seg.get("text") or ""
        acc = scores.setdefault(sp, {"q": 0.0, "doc": 0.0, "pat": 0.0, "n": 0.0})
        acc["n"] += 1
        acc["q"] += 2.0 if "?" in text else 0.0
        acc["q"] += 1.0 if _count_markers(text, QUESTION_WORDS) else 0.0
        acc["doc"] += _count_markers(text, DOCTOR_MARKERS)
        acc["pat"] += _count_markers(text, PATIENT_MARKERS)
    out = {}
    for sp, acc in scores.items():
        # peso maior para a diferença doc-pat; perguntas contam como indício médico
        out[sp] = (acc["doc"] - acc["pat"]) + 0.5 * acc["q"] / max(1.0, acc["n"]) * 3
    return out


def heuristic_roles(segments: list[dict[str, Any]], max_speakers: int = 2) -> dict[str, str]:
    scores = heuristic_scores(segments)
    speakers = sorted(scores, key=lambda s: -scores[s])
    if len(speakers) > max_speakers:
        speakers = speakers[:max_speakers]
    if not speakers:
        return {}
    if len(speakers) == 1:
        return {speakers[0]: "MEDICO"}
    return {speakers[0]: "MEDICO", speakers[1]: "PACIENTE"}


RoleSources = dict[str, str]  # speaker -> MEDICO|PACIENTE


def combine_roles(*sources: RoleSources) -> tuple[RoleSources, bool, list[str]]:
    """Combina fontes (ordem = prioridade). Retorna (papéis, consenso, divergentes).

    Consenso só quando todas as fontes que opinaram concordam; qualquer
    divergência marca os falantes para confirmação manual (mitigação #5).
    """
    speakers: set[str] = set()
    for src in sources:
        speakers.update(src)
    roles: RoleSources = {}
    divergent: list[str] = []
    for sp in speakers:
        votes = [src[sp] for src in sources if sp in src]
        if not votes:
            continue
        winner = max(set(votes), key=votes.count)
        roles[sp] = winner
        if any(v != winner for v in votes):
            divergent.append(sp)
    consensus = not divergent
    return roles, consensus, divergent


def parse_llm_roles_reply(reply: str, speakers: list[str]) -> RoleSources:
    """Extrai {'SPEAKER_00': 'MEDICO', ...} da resposta JSON do LLM."""
    m = re.search(r"\{.*\}", reply, re.DOTALL)
    import json

    data = json.loads(m.group(0)) if m else {}
    out: RoleSources = {}
    for sp in speakers:
        v = str(data.get(sp, "")).upper()
        if v in ("MEDICO", "PACIENTE"):
            out[sp] = v
    return out


def swap_roles(roles: RoleSources) -> RoleSources:
    return {sp: ("PACIENTE" if r == "MEDICO" else "MEDICO") for sp, r in roles.items()}


# Tipagem do verificador LLM (injetado pelo worker; evita dependência aqui).
RoleVerifier = Callable[[str], RoleSources]
