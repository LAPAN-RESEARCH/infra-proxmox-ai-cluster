from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import _is_loopback, _validate_credentials
from app.config import get_settings
from app.ollama import OllamaClient
from app.retrieval import RagRetriever
from app.rag import build_chat_payload, latest_user_query
from app.schemas import ChatCompletionRequest, EmbeddingRequest, RetrieveRequest


@pytest.fixture(autouse=True)
def api_key(monkeypatch):
    monkeypatch.setenv("AI_API_KEY", "test-token")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_auth_accepts_only_matching_bearer_token():
    _validate_credentials(HTTPAuthorizationCredentials(scheme="Bearer", credentials="test-token"))

    with pytest.raises(HTTPException) as exc:
        _validate_credentials(HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong"))
    assert exc.value.status_code == 401


def test_loopback_detection_for_local_healthcheck():
    assert _is_loopback("127.0.0.1")
    assert _is_loopback("::1")
    assert not _is_loopback("100.64.0.10")


def test_openai_request_schemas_accept_gateway_extensions():
    chat = ChatCompletionRequest.model_validate(
        {
            "model": "qwen3:8b",
            "messages": [{"role": "user", "content": "question"}],
            "rag": {"enabled": True, "top_k": 5, "rerank": False, "include_citations": True},
        }
    )
    assert chat.rag and chat.rag.enabled
    assert latest_user_query(chat.messages) == "question"

    embeddings = EmbeddingRequest.model_validate({"input": ["a", "b"], "model": "bge-m3"})
    assert embeddings.input == ["a", "b"]

    retrieve = RetrieveRequest.model_validate({"query": "question", "filters": {"citation_key": "smith2024"}})
    assert retrieve.filters == {"citation_key": "smith2024"}


def test_chat_payload_maps_openai_options_to_ollama():
    payload = build_chat_payload(
        "qwen3:8b",
        [{"role": "developer", "content": "Be concise."}, {"role": "user", "content": "Hello"}],
        {"temperature": 0.2, "max_tokens": 64, "response_format": {"type": "json_object"}},
    )
    assert payload["model"] == "qwen3:8b"
    assert payload["messages"][0] == {"role": "system", "content": "Be concise."}
    assert payload["options"] == {"temperature": 0.2, "num_predict": 64}
    assert payload["format"] == "json"


def test_rerank_timeout_setting_can_be_overridden(monkeypatch):
    monkeypatch.setenv("AI_API_RERANK_TIMEOUT_SECONDS", "3")
    get_settings.cache_clear()
    assert get_settings().rerank_timeout_seconds == 3


def test_retrieve_skips_cold_reranker(monkeypatch):
    settings = get_settings()
    retriever = RagRetriever(settings, OllamaClient("http://example.invalid"))
    retriever.reranker._ready = False

    async def fake_dense(*args, **kwargs):
        return [{"chunk_id": "a", "text": "alpha", "citation_key": "one"}]

    def fake_bm25(*args, **kwargs):
        return [{"chunk_id": "a", "text": "alpha", "citation_key": "one"}]

    monkeypatch.setattr(retriever, "_dense_search", fake_dense)
    monkeypatch.setattr(retriever, "_bm25_search", fake_bm25)
    monkeypatch.setattr(retriever.reranker, "rerank", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("rerank should not run")))

    result = asyncio.run(retriever.retrieve("query", top_k=1, rerank=True))
    assert result.rows[0]["chunk_id"] == "a"
    assert result.warnings == ["Reranker not warmed yet, returning fused results"]
