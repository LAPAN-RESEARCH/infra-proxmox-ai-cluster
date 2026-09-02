from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_json(self, path: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}{path}")
            resp.raise_for_status()
            return resp.json()

    async def post_json(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}{path}", json=body)
            resp.raise_for_status()
            return resp.json()

    async def list_models(self) -> dict[str, Any]:
        return await self.get_json("/api/tags")

    async def embed(self, model: str, inputs: str | list[str]) -> list[list[float]]:
        resp = await self.post_json("/api/embed", {"model": model, "input": inputs})
        vectors = resp.get("embeddings")
        if not isinstance(vectors, list) or not vectors:
            raise RuntimeError(f"Ollama did not return embeddings for model {model}")
        return vectors

    async def chat(self, body: dict[str, Any]) -> dict[str, Any]:
        payload = {**body, "stream": False}
        return await self.post_json("/api/chat", payload)

    async def stream_chat(self, body: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        payload = {**body, "stream": True}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line:
                        yield json.loads(line)
