from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def _env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    api_key: str = Field(default_factory=lambda: os.environ.get("AI_API_KEY", ""))
    ollama_base_url: str = Field(default_factory=lambda: os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434"))
    qdrant_url: str = Field(default_factory=lambda: os.environ.get("QDRANT_URL", "http://qdrant:6333"))
    qdrant_api_key: str = Field(default_factory=lambda: os.environ.get("QDRANT_API_KEY", ""))
    rag_config_path: str = Field(
        default_factory=lambda: os.environ.get("RAG_CONFIG", "/srv/ai/rag/configs/research-platform.yaml")
    )
    rag_collection: str = Field(default_factory=lambda: os.environ.get("RAG_COLLECTION", "research_chunks_bge_m3"))
    reranker_model: str = Field(default_factory=lambda: os.environ.get("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"))
    default_chat_model: str = Field(default_factory=lambda: os.environ.get("OLLAMA_CHAT_MODEL", "qwen3:8b"))
    default_embedding_model: str = Field(default_factory=lambda: os.environ.get("OLLAMA_EMBEDDING_MODEL", "bge-m3"))
    hf_hub_cache: str = Field(
        default_factory=lambda: os.environ.get("HF_HUB_CACHE", "/home/app/.cache/huggingface/hub")
    )
    allow_local_healthz: bool = Field(
        default_factory=lambda: _env_bool("AI_API_ALLOW_LOCAL_HEALTHZ", True)
    )
    request_timeout_seconds: float = Field(
        default_factory=lambda: float(os.environ.get("AI_API_REQUEST_TIMEOUT_SECONDS", "120"))
    )
    rerank_timeout_seconds: float = Field(
        default_factory=lambda: float(os.environ.get("AI_API_RERANK_TIMEOUT_SECONDS", "15"))
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    os.environ.setdefault("HF_HUB_CACHE", settings.hf_hub_cache)
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", settings.hf_hub_cache)
    return settings


def load_rag_config(settings: Settings | None = None) -> dict[str, Any]:
    settings = settings or get_settings()
    path = Path(settings.rag_config_path)
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    else:
        config = {}

    config.setdefault("rag", {})
    config.setdefault("embedding", {})
    config.setdefault("qdrant", {})
    config.setdefault("chunking", {})
    config.setdefault("retrieval", {})

    config["embedding"]["base_url"] = settings.ollama_base_url
    config["embedding"]["model"] = settings.default_embedding_model
    config["qdrant"]["url"] = settings.qdrant_url
    config["qdrant"]["collection"] = settings.rag_collection
    config["rag"]["collection"] = settings.rag_collection
    config["rag"]["embedding_model"] = settings.default_embedding_model
    config["rag"]["reranker_model"] = settings.reranker_model
    config["chunking"].setdefault("chunks_path", "/srv/ai/ingest/chunks/chunks.jsonl")
    config["retrieval"].setdefault("bm25_candidate_k", 50)
    config["retrieval"].setdefault("dense_candidate_k", 50)
    config["retrieval"].setdefault("rerank_candidate_k", 50)
    config["retrieval"].setdefault("final_k", 10)
    return config
