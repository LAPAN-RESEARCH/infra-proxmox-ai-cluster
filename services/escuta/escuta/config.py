"""Configuração por ambiente (padrão ESCUTA_*)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "") or default)
    except ValueError:
        return default


@dataclass
class Settings:
    data_dir: Path = field(default_factory=lambda: Path(os.environ.get("ESCUTA_DATA_DIR", "/srv/ai/clinical")))

    # Retenção do áudio bruto (decisão 2026-09-24: 90 dias no piloto).
    retention_days: int = field(default_factory=lambda: _int_env("ESCUTA_RETENTION_DAYS", 90))

    # ASR (Speaches/WLK, OpenAI-compatible).
    asr_backend: str = field(default_factory=lambda: os.environ.get("ESCUTA_ASR_BACKEND", "http"))
    asr_url: str = field(default_factory=lambda: os.environ.get(
        "ESCUTA_ASR_URL", "http://speaches:8000/v1/audio/transcriptions"))
    asr_model: str = field(default_factory=lambda: os.environ.get(
        "ESCUTA_ASR_MODEL", "Systran/faster-whisper-large-v3-turbo"))
    asr_api_key_env: str = field(default_factory=lambda: os.environ.get("ESCUTA_ASR_API_KEY_ENV", "SPEACHES_API_KEY"))
    asr_language: str = "pt"

    # Realtime (WLK).
    wlk_url: str = field(default_factory=lambda: os.environ.get(
        "ESCUTA_WLK_URL", "ws://whisper-livekit:8000/asr"))
    wlk_token_env: str = field(default_factory=lambda: os.environ.get("ESCUTA_WLK_TOKEN_ENV", "WLK_API_TOKEN"))

    # LLM: nativo Ollama (/api/chat, think=false) por padrão — extração
    # estruturada não usa raciocínio nem RAG; OpenAI-compatible também suportado.
    llm_backend: str = field(default_factory=lambda: os.environ.get("ESCUTA_LLM_BACKEND", "http"))
    llm_url: str = field(default_factory=lambda: os.environ.get(
        "ESCUTA_LLM_URL", "http://ollama:11434/api/chat"))
    llm_api_key_env: str = field(default_factory=lambda: os.environ.get("ESCUTA_LLM_API_KEY_ENV", "AI_API_KEY"))
    soap_model: str = field(default_factory=lambda: os.environ.get("ESCUTA_SOAP_MODEL", "qwen3:8b"))
    verify_model: str = field(default_factory=lambda: os.environ.get("ESCUTA_VERIFY_MODEL", "qwen3:8b"))

    # Diarização (opcional; ausente => transcript mono-falante sinalizado).
    diar_max_speakers: int = field(default_factory=lambda: _int_env("ESCUTA_DIAR_MAX_SPEAKERS", 2))

    # Lock de GPU / preemptação do titular (política: fila clínica primeiro).
    run_dir: Path = field(default_factory=lambda: Path(os.environ.get("ESCUTA_RUN_DIR", "/run/escuta")))
    ollama_container: str = field(default_factory=lambda: os.environ.get("ESCUTA_OLLAMA_CONTAINER", "ollama"))
    ollama_model: str = field(default_factory=lambda: os.environ.get("ESCUTA_OLLAMA_MODEL", "gpt-oss:20b"))
    unload_titular_on_job: bool = field(default_factory=lambda: os.environ.get(
        "ESCUTA_UNLOAD_TITULAR_ON_JOB", "1") not in ("0", "false", "no"))

    # Prompts externos (sobrepõe os padrões embutidos em prompts.py).
    prompts_dir: Path | None = field(default_factory=lambda: (
        Path(p) if (p := os.environ.get("ESCUTA_PROMPTS_DIR")) else None))

    # VAD de borda no worker (o endpoint também aplica o seu).
    vad_min_speech_ms: int = field(default_factory=lambda: _int_env("ESCUTA_VAD_MIN_SPEECH_MS", 250))

    @property
    def audio_dir(self) -> Path:
        return self.data_dir / "audio"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "escuta.db"

    def ensure_dirs(self) -> None:
        for p in (self.data_dir, self.audio_dir, self.run_dir):
            p.mkdir(parents=True, exist_ok=True)
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def env_secret(self, env_name: str) -> str | None:
        return os.environ.get(env_name) or None
