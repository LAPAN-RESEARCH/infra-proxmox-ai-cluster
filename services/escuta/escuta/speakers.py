"""Diarização offline (pyannote-audio 4.x) e enrollment ECAPA — opcionais.

Sem pyannote/torch instalados (imagem base), o worker segue com
`turns=[]` e o transcript sai mono-falante sinalizado; sem speechbrain, o
enrollment é pulado e a atribuição de papéis cai para heurística + LLM.
"""
from __future__ import annotations

import struct
from pathlib import Path
from typing import Any

from .config import Settings


class Diarizer:
    """pyannote-audio: segmentação + embeddings + clustering (máx. N falantes)."""

    def __init__(self, settings: Settings) -> None:
        try:
            from pyannote.audio import Pipeline
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "diarização requer pyannote.audio (pip install -r requirements-gpu.txt)"
            ) from exc
        import os

        self._settings = settings
        token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        # pyannote >=4 aceita `token=`; `use_auth_token=` foi removido.
        auth_kwargs = ({"token": token} if token else {})
        # 3.1 é gated (exige aceite de termos + token); community-1 é CC-BY-4.0
        # e funciona sem token. Tenta ambos e degrada se nenhum baixar.
        self._pipeline = None
        last_exc: Exception | None = None
        for model in ("pyannote/speaker-diarization-3.1", "pyannote/speaker-diarization-community-1"):
            try:
                self._pipeline = Pipeline.from_pretrained(model, **auth_kwargs)
                self._model_name = model
                break
            except TypeError:
                # versões antigas do pyannote ainda usam use_auth_token
                try:
                    self._pipeline = Pipeline.from_pretrained(model, use_auth_token=token)
                    self._model_name = model
                    break
                except Exception as exc:
                    last_exc = exc
            except Exception as exc:
                last_exc = exc
        if self._pipeline is None:
            raise RuntimeError(
                f"nenhum pipeline pyannote disponível (HF_TOKEN ausente/gated): {last_exc}"
            )

    def turns(self, wav16k: Path) -> list[dict[str, Any]]:
        # Consulta médico×paciente: nº exato de falantes (com apenas teto
        # max_speakers, o clustering do community-1 colapsava para 1).
        n = self._settings.diar_max_speakers
        kwargs = {"num_speakers": n} if n == 2 else {"max_speakers": n}
        diar = self._pipeline(str(wav16k), **kwargs)
        ann = _as_annotation(diar)
        return [{"start": float(t.start), "end": float(t.end), "speaker": sp}
                for t, _, sp in ann.itertracks(yield_label=True)]


def _as_annotation(diar: Any) -> Any:
    """pyannote 3.x devolve Annotation direto; 4.x/community-1 devolve
    DiarizeOutput — o Annotation clássico vive em .speaker_diarization."""
    if hasattr(diar, "itertracks"):
        return diar
    for attr in ("speaker_diarization", "exclusive_speaker_diarization"):
        cand = getattr(diar, attr, None)
        if callable(cand):
            try:
                cand = cand()
            except Exception:
                continue
        if cand is not None and hasattr(cand, "itertracks"):
            return cand
    raise RuntimeError(f"saída de diarização não reconhecida: {type(diar).__name__}")


class EcapaEnroller:
    """Enrollment do médico: embedding ECAPA-TDNN (192-dim) por cosine matching."""

    def __init__(self) -> None:
        try:
            from speechbrain.inference.speaker import EncoderClassifier
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "enrollment requer speechbrain (pip install -r requirements-gpu.txt)"
            ) from exc
        self._model = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir="/tmp/ecapa", run_opts={"device": "cpu"},
        )

    def embed(self, wav16k: Path, start_s: float | None = None, end_s: float | None = None) -> bytes:
        import torch

        clip = wav16k
        if start_s is not None or end_s is not None:
            clip = wav16k.with_suffix(f".clip{wav16k.suffix}")
            _cut_wav(wav16k, clip, start_s or 0.0, end_s)
        wav = self._model.load_audio(str(clip))
        emb = self._model.encode_batch(torch.tensor(wav).unsqueeze(0))
        return _pack_embedding(emb.squeeze().detach().cpu().numpy())


def _cut_wav(src: Path, dst: Path, start_s: float, end_s: float | None) -> None:
    import wave

    with wave.open(str(src), "rb") as w:
        rate = w.getframerate()
        w.setpos(int(start_s * rate))
        frames = w.readframes(int(((end_s if end_s is not None else w.getnframes() / rate) - start_s) * rate))
    with wave.open(str(dst), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(frames)


def _pack_embedding(vec: Any) -> bytes:
    return struct.pack(f"<{len(vec)}f", * [float(x) for x in vec])


def _unpack_embedding(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"<{n}f", blob[: n * 4]))


def cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return -1.0
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5 or 1e-9
    nb = sum(y * y for y in b) ** 0.5 or 1e-9
    return num / (na * nb)


def match_speaker(turn_embedding: bytes, reference: bytes, threshold: float = 0.5) -> float:
    """Score contra o enrollment do médico; >= threshold => é o médico."""
    return cosine(_unpack_embedding(turn_embedding), _unpack_embedding(reference))
