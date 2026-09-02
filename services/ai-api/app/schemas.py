from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CompatModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class ChatMessage(CompatModel):
    role: str
    content: Any = None
    name: str | None = None


class RagOptions(CompatModel):
    enabled: bool = False
    top_k: int | None = Field(default=None, ge=1, le=50)
    rerank: bool = True
    include_citations: bool = True
    filters: dict[str, Any] | None = None
    metadata_filters: dict[str, Any] | None = None


class ChatCompletionRequest(CompatModel):
    model: str | None = None
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: str | list[str] | None = None
    response_format: dict[str, Any] | None = None
    rag: RagOptions | None = None


class EmbeddingRequest(CompatModel):
    input: str | list[str]
    model: str | None = None


class RetrieveRequest(CompatModel):
    query: str
    top_k: int | None = Field(default=None, ge=1, le=50)
    rerank: bool = True
    filters: dict[str, Any] | None = None
    metadata_filters: dict[str, Any] | None = None
