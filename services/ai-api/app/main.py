from __future__ import annotations

import json
import time
import uuid
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse

from .auth import require_auth, require_health_auth
from .config import get_settings
from .ollama import OllamaClient
from .rag import build_chat_payload, build_context, latest_user_query
from .retrieval import RagRetriever, format_retrieval_row, token_estimate
from .schemas import ChatCompletionRequest, EmbeddingRequest, RetrieveRequest

settings = get_settings()
ollama = OllamaClient(settings.ollama_base_url, timeout=settings.request_timeout_seconds)
retriever = RagRetriever(settings, ollama)

app = FastAPI(title="Local AI API Gateway", version="1.0.0")


def _now() -> int:
    return int(time.time())


def _openai_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex}"


def _usage_from_ollama(resp: dict[str, Any]) -> dict[str, int]:
    prompt_tokens = int(resp.get("prompt_eval_count") or 0)
    completion_tokens = int(resp.get("eval_count") or 0)
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
    }


async def _dependency_status() -> dict[str, Any]:
    deps: dict[str, Any] = {}
    try:
        tags = await ollama.list_models()
        deps["ollama"] = {"status": "ok", "models": len(tags.get("models", []))}
    except Exception as exc:
        deps["ollama"] = {"status": "error", "detail": str(exc)}

    headers = {"api-key": settings.qdrant_api_key} if settings.qdrant_api_key else {}
    url = f"{settings.qdrant_url.rstrip('/')}/collections/{settings.rag_collection}"
    try:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
        deps["qdrant"] = {"status": "ok", "collection": settings.rag_collection}
    except Exception as exc:
        deps["qdrant"] = {"status": "error", "collection": settings.rag_collection, "detail": str(exc)}
    return deps


@app.on_event("startup")
async def _warm_reranker() -> None:
    import asyncio as _asyncio

    _asyncio.create_task(retriever.preload_reranker())


@app.get("/healthz", dependencies=[Depends(require_health_auth)])
async def healthz() -> dict[str, Any]:
    deps = await _dependency_status()
    healthy = all(dep.get("status") == "ok" for dep in deps.values())
    return {
        "status": "ok" if healthy else "degraded",
        "auth_configured": bool(settings.api_key),
        "dependencies": deps,
    }


@app.get("/v1/models", dependencies=[Depends(require_auth)])
async def models() -> dict[str, Any]:
    tags = await ollama.list_models()
    data = []
    for model in tags.get("models", []):
        name = model.get("name") or model.get("model")
        if not name:
            continue
        data.append(
            {
                "id": name,
                "object": "model",
                "created": 0,
                "owned_by": "ollama",
            }
        )
    return {"object": "list", "data": data}


@app.post("/v1/embeddings", dependencies=[Depends(require_auth)])
async def embeddings(req: EmbeddingRequest) -> dict[str, Any]:
    model = req.model or settings.default_embedding_model
    inputs = [req.input] if isinstance(req.input, str) else req.input
    vectors = await ollama.embed(model, inputs)
    return {
        "object": "list",
        "model": model,
        "data": [
            {"object": "embedding", "embedding": vector, "index": index}
            for index, vector in enumerate(vectors)
        ],
        "usage": {
            "prompt_tokens": sum(token_estimate(text) for text in inputs),
            "total_tokens": sum(token_estimate(text) for text in inputs),
        },
    }


@app.post("/v1/rag/retrieve", dependencies=[Depends(require_auth)])
async def retrieve(req: RetrieveRequest) -> dict[str, Any]:
    filters = req.filters or req.metadata_filters
    result_set = await retriever.retrieve(
        req.query,
        top_k=req.top_k,
        rerank=req.rerank,
        filters=filters,
    )
    return {
        "object": "list",
        "query": req.query,
        "data": [
            format_retrieval_row(row, index=index)
            for index, row in enumerate(result_set.rows, start=1)
        ],
        "warnings": result_set.warnings,
    }


async def _prepare_chat(req: ChatCompletionRequest) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    model = req.model or settings.default_chat_model
    request_data = req.model_dump(exclude_none=True)
    messages = [message.model_dump(exclude_none=True) for message in req.messages]
    citations: list[dict[str, Any]] = []
    warnings: list[str] = []

    if req.rag and req.rag.enabled:
        try:
            query = latest_user_query(req.messages)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        filters = req.rag.filters or req.rag.metadata_filters
        result_set = await retriever.retrieve(
            query,
            top_k=req.rag.top_k,
            rerank=req.rag.rerank,
            filters=filters,
        )
        context, citations = build_context(result_set.rows)
        warnings.extend(result_set.warnings)
        messages = [{"role": "system", "content": context}, *messages]

    return model, messages, citations if (req.rag and req.rag.include_citations) else [], warnings


@app.post("/v1/chat/completions", dependencies=[Depends(require_auth)])
async def chat_completions(req: ChatCompletionRequest) -> Any:
    model, messages, citations, warnings = await _prepare_chat(req)
    request_data = req.model_dump(exclude_none=True)
    payload = build_chat_payload(model, messages, request_data)

    if req.stream:
        return StreamingResponse(
            _stream_openai_chat(model, payload, citations, warnings),
            media_type="text/event-stream",
        )

    resp = await ollama.chat(payload)
    message = resp.get("message") or {}
    response = {
        "id": _openai_id("chatcmpl"),
        "object": "chat.completion",
        "created": _now(),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": message.get("content", "")},
                "finish_reason": resp.get("done_reason") or "stop",
            }
        ],
        "usage": _usage_from_ollama(resp),
    }
    if citations:
        response["citations"] = citations
    if warnings:
        response["warnings"] = warnings
    return response


async def _stream_openai_chat(
    model: str,
    payload: dict[str, Any],
    citations: list[dict[str, Any]],
    warnings: list[str],
):
    chunk_id = _openai_id("chatcmpl")
    created = _now()
    role_chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    }
    yield f"data: {json.dumps(role_chunk)}\n\n"

    async for event in ollama.stream_chat(payload):
        message = event.get("message") or {}
        content = message.get("content")
        if content:
            chunk = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        if event.get("done"):
            final_chunk: dict[str, Any] = {
                "id": chunk_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": model,
                "choices": [{"index": 0, "delta": {}, "finish_reason": event.get("done_reason") or "stop"}],
            }
            if citations:
                final_chunk["citations"] = citations
            if warnings:
                final_chunk["warnings"] = warnings
            yield f"data: {json.dumps(final_chunk)}\n\n"
            break
    yield "data: [DONE]\n\n"
