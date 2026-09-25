"""Alinhamento temporal palavra × locutor (lógica pura, testável).

Recebe os timestamps word-level do ASR (faster-whisper `word_timestamps=True`)
e os turnos de fala da diarização, e reconstrói segmentos homogêneos por
locutor — a base da atribuição exata Médico/Paciente do Pilar 3.
"""
from __future__ import annotations

from typing import Any

Word = dict[str, Any]  # {w, s, e, p?}


def overlap(a0: float, a1: float, b0: float, b1: float) -> float:
    return max(0.0, min(a1, b1) - max(a0, b0))


def assign_word_speaker(word: Word, turns: list[dict[str, Any]],
                        tolerance_s: float = 0.25) -> str | None:
    """Palavra pertence ao turno com maior sobreposição temporal.

    Empate ou palavra fora de todo turno (até `tolerance_s`) → turno mais
    próximo; palavra órfã real → None (fica marcada no segmento).
    """
    best, best_ov = None, 0.0
    for t in turns:
        ov = overlap(word["s"], word["e"], t["start"], t["end"])
        if ov > best_ov:
            best, best_ov = t["speaker"], ov
    if best is not None and best_ov > 0:
        return best
    mid = (word["s"] + word["e"]) / 2
    nearest, nearest_gap = None, float("inf")
    for t in turns:
        gap = min(abs(mid - t["start"]), abs(mid - t["end"]))
        if gap < nearest_gap:
            nearest, nearest_gap = t["speaker"], gap
    if nearest is not None and nearest_gap <= tolerance_s:
        return nearest
    return None


def resegment_by_speaker(segments: list[dict[str, Any]],
                         turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Segmentos ASR + turnos -> segmentos com locutor homogêneo.

    Quebra um segmento do ASR onde a palavra muda de locutor (trocas rápidas
    de turno ficam corretas palavra a palavra). Sem turnos disponíveis,
    devolve os segmentos com speaker=None.
    """
    out: list[dict[str, Any]] = []
    for seg in segments:
        words: list[Word] = [
            {"w": w["w"], "s": float(w["s"]), "e": float(w["e"]),
             "speaker": assign_word_speaker(w, turns) if turns else None}
            for w in seg.get("words") or []
        ]
        if not words:
            text = (seg.get("text") or "").strip()
            if not text:
                continue
            speaker = None
            if turns:
                sp = assign_word_speaker(
                    {"s": float(seg.get("start", 0)), "e": float(seg.get("end", 0))}, turns)
                speaker = sp
            out.append({"start": seg.get("start"), "end": seg.get("end"),
                        "speaker": speaker, "text": text, "words": []})
            continue
        run: list[Word] = []
        for w in words:
            if run and w["speaker"] != run[-1]["speaker"]:
                out.append(_mk(run))
                run = []
            run.append(w)
        if run:
            out.append(_mk(run))
    return out


def _mk(run: list[Word]) -> dict[str, Any]:
    return {
        "start": run[0]["s"],
        "end": run[-1]["e"],
        "speaker": run[0]["speaker"],
        "text": " ".join(w["w"] for w in run).strip(),
        "words": run,
    }


def format_ts(seconds: float) -> str:
    s = int(round(seconds))
    return f"{s // 60:02d}:{s % 60:02d}"


def build_dialogue(segments: list[dict[str, Any]],
                   role_of: dict[str, str] | None = None) -> str:
    """Transcrição literal auditável: `[mm:ss] PAPEL: texto` por segmento."""
    role_of = role_of or {}
    lines = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        who = role_of.get(seg.get("speaker") or "", seg.get("speaker") or "?")
        lines.append(f"[{format_ts(float(seg['start']))}] {who}: {text}")
    return "\n".join(lines)
