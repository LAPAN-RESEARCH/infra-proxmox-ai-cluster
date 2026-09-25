"""Áudio: decodificação/encode via ffmpeg e gravação incremental WAV.

- Processamento e transporte interno: PCM 16 kHz mono s16le (nativo do Whisper).
- Armazenamento (retenção de 90 dias): Opus em OGG (~7-10 MB/h).
"""
from __future__ import annotations

import shutil
import subprocess
import wave
from pathlib import Path

SAMPLE_RATE = 16_000


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def decode_to_wav16k(src: Path, dst: Path) -> Path:
    """Qualquer entrada comum (opus/ogg/webm/mp3/m4a/wav) -> wav 16k mono s16."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(src), "-ac", "1", "-ar", str(SAMPLE_RATE), "-sample_fmt", "s16", str(dst)],
        check=True,
    )
    return dst


def encode_opus(wav: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(wav), "-c:a", "libopus", "-b:a", "24k", str(dst)],
        check=True,
    )
    return dst


def wav_duration_s(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / float(w.getframerate())


class WavAccumulator:
    """Gravação servidor-side: acumula chunks PCM 16k s16le num wav crescente.

    A aba do navegador é só display — se cair, o arquivo no servidor continua
    íntegro até o último chunk recebido (mitigação #7 da matriz de falhas).
    """

    def __init__(self, path: Path, rate: int = SAMPLE_RATE) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = open(path, "wb")
        self._w = wave.open(self._fh, "wb")
        self._w.setnchannels(1)
        self._w.setsampwidth(2)
        self._w.setframerate(rate)
        self.path = path
        self.rate = rate

    def write(self, pcm: bytes) -> None:
        if len(pcm) % 2:
            pcm = pcm[:-1]  # frame Int16 partido por chunk de rede
        self._w.writeframes(pcm)

    def duration_s(self) -> float:
        return self._w.getnframes() / float(self.rate)

    def close(self) -> float:
        duration = self.duration_s()
        self._w.close()
        self._fh.close()
        return duration


def apply_highpass(wav_in: Path, wav_out: Path, hz: int = 90) -> Path:
    """Filtro passa-alta leve (ar-condicionado/manuseio) — plano, Pilar 1."""
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
         "-i", str(wav_in), "-af", f"highpass=f={hz}", "-ac", "1",
         "-ar", str(SAMPLE_RATE), "-sample_fmt", "s16", str(wav_out)],
        check=True,
    )
    return wav_out
