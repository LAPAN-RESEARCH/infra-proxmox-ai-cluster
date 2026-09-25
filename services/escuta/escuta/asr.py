"""Cliente ASR: backends http (Speaches/WLK), embedded (faster-whisper com o
perfil determinístico completo do Pilar 2) e stub (dev/testes sem GPU).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import Settings

# Perfil determinístico (Pilar 2 do plano). O endpoint OpenAI-compatible do
# Speaches só aceita um subconjunto; o modo `embedded` aplica tudo.
DETERMINISTIC_PARAMS: dict[str, Any] = {
    "language": "pt",
    "beam_size": 5,
    "best_of": 5,
    "temperature": (0.0, 0.2, 0.4, 0.6, 0.8, 1.0),  # fallback = retry anti-loop
    "condition_on_previous_text": False,
    "vad_filter": True,
    "no_speech_threshold": 0.6,
    "log_prob_threshold": -1.0,
    "compression_ratio_threshold": 2.4,
    "word_timestamps": True,
}

INITIAL_PROMPT = (
    "Consulta médica em português do Brasil. Terminologia clínica, sintomas, "
    "dosagens de medicamentos em mg/mL, exames e anatomia oftalmológica."
)


class AsrError(RuntimeError):
    pass


def normalize_segments(raw_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Chaves canônicas: words=[{w,s,e,p}], start/end/text por segmento.

    Se o backend não devolver word timestamps, interpola linearmente dentro do
    segmento (aproximação documentada; a atribuição de locutor por palavra
    degrada graciosamente para o nível do segmento).
    """
    out = []
    for seg in raw_segments:
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        start = float(seg.get("start", 0))
        end = float(seg.get("end", start))
        words = []
        for w in seg.get("words") or []:
            word = (w.get("word") or w.get("w") or "").strip()
            if not word:
                continue
            words.append({"w": word, "s": float(w.get("start", w.get("s", start))),
                          "e": float(w.get("end", w.get("e", end))),
                          "p": float(w.get("probability", w.get("p", 0.0)))})
        if not words:
            words = _interpolate_words(text, start, end)
        out.append({"start": start, "end": end, "text": text, "words": words})
    return out


def _interpolate_words(text: str, start: float, end: float) -> list[dict[str, Any]]:
    tokens = text.split()
    if not tokens:
        return []
    span = max(end - start, 0.1) / len(tokens)
    return [
        {"w": t, "s": start + i * span, "e": start + (i + 1) * span, "p": 0.0}
        for i, t in enumerate(tokens)
    ]


class HttpAsr:
    """Speaches/WLK via multipart POST (OpenAI-compatible, verbose_json)."""

    def __init__(self, settings: Settings) -> None:
        import httpx

        self._settings = settings
        self._client = httpx.Client(timeout=3600.0)
        self._key = settings.env_secret(settings.asr_api_key_env)

    def transcribe(self, wav16k: Path) -> dict[str, Any]:
        model = self._settings.asr_model
        with open(wav16k, "rb") as fh:
            files = {"file": (wav16k.name, fh, "audio/wav")}
            data = {"model": model, "language": self._settings.asr_language,
                    "response_format": "verbose_json", "temperature": "0"}
            headers = {"Authorization": f"Bearer {self._key}"} if self._key else {}
            resp = self._client.post(self._settings.asr_url, files=files, data=data, headers=headers)
        if resp.status_code >= 400:
            raise AsrError(f"ASR {resp.status_code}: {resp.text[:300]}")
        payload = resp.json()
        return {"model": model, "params": {"backend": "http", "language": self._settings.asr_language},
                "segments": normalize_segments(payload.get("segments") or []),
                "text": payload.get("text", "")}


class EmbeddedAsr:
    """faster-whisper in-process (CTranslate2) com o perfil determinístico."""

    def __init__(self, settings: Settings, model_name: str | None = None) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:  # pragma: no cover - exige extras GPU
            raise AsrError(
                "backend 'embedded' requer faster-whisper (pip install -r requirements-gpu.txt)"
            ) from exc
        self._model_name = model_name or settings.asr_model.split("/")[-1].replace("faster-whisper-", "")
        self._params = dict(DETERMINISTIC_PARAMS)
        self._model = WhisperModel(self._model_name, device="cuda", compute_type="float16")

    def transcribe(self, wav16k: Path) -> dict[str, Any]:
        segments_iter, info = self._model.transcribe(str(wav16k), initial_prompt=INITIAL_PROMPT,
                                                     **self._params)
        raw = []
        for seg in segments_iter:
            words = [{"word": w.word, "start": w.start, "end": w.end, "probability": w.probability}
                     for w in (seg.words or [])]
            raw.append({"start": seg.start, "end": seg.end, "text": seg.text, "words": words})
        return {"model": self._model_name, "params": {**self._params, "backend": "embedded"},
                "segments": normalize_segments(raw), "text": ""}


_STUB_LINES = [
    "Bom dia, pode sentar. O que está sentando hoje?",
    "Doutor, meus olhos estão ardendo muito no fim do dia.",
    "Há quanto tempo começou esse desconforto?",
    "Uns dois meses, mas piorou nas últimas semanas.",
    "Já usou algum colírio lubrificante antes?",
    "Usei um de carboximetilcelulose a um por cento, mas parei.",
    "Vou prescrever colírio sem conservante, uma gota quatro vezes ao dia.",
    "Preciso voltar quando, doutor?",
    "Retorno em trinta dias com reavaliação do exame.",
]


class StubAsr:
    """Backend determinístico sem rede: devolve diálogo fictício em 2 falantes.

    Para desenvolvimento/testes do pipeline (backend=stub) — nunca produção.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def transcribe(self, wav16k: Path) -> dict[str, Any]:
        from .audio import wav_duration_s

        total = max(wav_duration_s(wav16k), 1.0)
        seg_s = total / len(_STUB_LINES)
        segments = []
        for i, text in enumerate(_STUB_LINES):
            start, end = i * seg_s, (i + 1) * seg_s
            speaker = "SPEAKER_00" if i % 2 == 0 else "SPEAKER_01"
            segments.append({"start": round(start, 2), "end": round(end, 2), "text": text,
                             "words": _interpolate_words(text, start, end),
                             "stub_speaker": speaker})
        return {"model": "stub", "params": {"backend": "stub"},
                "segments": segments, "text": " ".join(_STUB_LINES)}


def make_asr(settings: Settings) -> Any:
    backend = settings.asr_backend
    if backend == "http":
        return HttpAsr(settings)
    if backend == "embedded":
        return EmbeddedAsr(settings)
    if backend == "stub":
        return StubAsr(settings)
    raise AsrError(f"backend ASR desconhecido: {backend}")
