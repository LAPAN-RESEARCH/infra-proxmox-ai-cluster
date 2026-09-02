from __future__ import annotations

import asyncio
import json
import re
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from .config import Settings, load_rag_config
from .ollama import OllamaClient


def normalize_text(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def token_estimate(text: str) -> int:
    return max(1, len(re.findall(r"\S+", text)))


def snippet(text: str, max_chars: int = 700) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


@dataclass
class RetrievalSet:
    rows: list[dict[str, Any]]
    warnings: list[str]


class ChunkIndex:
    def __init__(self, chunks_path: str) -> None:
        self.chunks_path = Path(chunks_path)
        self._lock = threading.Lock()
        self._mtime: float | None = None
        self._chunks: list[dict[str, Any]] = []
        self._bm25: Any = None
        self._corpus: list[list[str]] = []

    def load(self) -> tuple[list[dict[str, Any]], Any]:
        mtime = self.chunks_path.stat().st_mtime if self.chunks_path.exists() else None
        with self._lock:
            if mtime == self._mtime and self._bm25 is not None:
                return self._chunks, self._bm25
            chunks = self._read_chunks()
            corpus = [normalize_text(row.get("text", "")).split() for row in chunks]
            from rank_bm25 import BM25Okapi

            self._chunks = chunks
            self._corpus = corpus
            self._bm25 = BM25Okapi(corpus) if corpus else None
            self._mtime = mtime
            return self._chunks, self._bm25

    def _read_chunks(self) -> list[dict[str, Any]]:
        if not self.chunks_path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.chunks_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    row = json.loads(line)
                    if row.get("chunk_id") and row.get("text"):
                        rows.append(row)
        return rows


class CrossEncoderReranker:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._lock = threading.Lock()
        self._model: Any = None
        self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def warm(self) -> None:
        with self._lock:
            if self._model is None:
                from sentence_transformers import CrossEncoder

                self._model = CrossEncoder(self.model_name)
                self._ready = True

    def rerank(self, query: str, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not candidates:
            return []
        with self._lock:
            if self._model is None:
                self.warm()
        pairs = [(query, candidate.get("text", "")) for candidate in candidates]
        scores = self._model.predict(pairs)
        reranked = []
        for candidate, score in zip(candidates, scores):
            reranked.append({**candidate, "rerank_score": float(score)})
        return sorted(reranked, key=lambda row: row.get("rerank_score", 0.0), reverse=True)


class RagRetriever:
    def __init__(self, settings: Settings, ollama: OllamaClient) -> None:
        self.settings = settings
        self.ollama = ollama
        self.config = load_rag_config(settings)
        self.chunk_index = ChunkIndex(self.config["chunking"]["chunks_path"])
        self.reranker = CrossEncoderReranker(self.config["rag"]["reranker_model"])

    async def preload_reranker(self) -> None:
        try:
            await asyncio.to_thread(self.reranker.warm)
        except Exception:
            pass

    async def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        rerank: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> RetrievalSet:
        retrieval_cfg = self.config["retrieval"]
        final_k = top_k or int(retrieval_cfg["final_k"])
        dense_task = self._dense_search(query, int(retrieval_cfg["dense_candidate_k"]), filters)
        bm25_task = asyncio.to_thread(self._bm25_search, query, int(retrieval_cfg["bm25_candidate_k"]), filters)
        warnings: list[str] = []

        dense_rows, bm25_rows = await asyncio.gather(dense_task, bm25_task)
        candidates = self._fuse_candidates(
            dense_rows,
            bm25_rows,
            limit=int(retrieval_cfg["rerank_candidate_k"]),
        )
        if rerank and candidates:
            if not self.reranker.ready:
                warnings.append("Reranker not warmed yet, returning fused results")
                return RetrievalSet(rows=candidates[:final_k], warnings=warnings)
            try:
                candidates = await asyncio.wait_for(
                    asyncio.to_thread(self.reranker.rerank, query, candidates),
                    timeout=self.settings.rerank_timeout_seconds,
                )
            except TimeoutError:
                warnings.append(
                    f"Reranker timed out after {self.settings.rerank_timeout_seconds:.0f}s, returning fused results"
                )
            except Exception as exc:
                warnings.append(f"Reranker unavailable, returning fused results: {exc}")
        return RetrievalSet(rows=candidates[:final_k], warnings=warnings)

    async def _dense_search(
        self,
        query: str,
        limit: int,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        vector = (await self.ollama.embed(self.config["embedding"]["model"], query))[0]
        qdrant = self.config["qdrant"]
        body: dict[str, Any] = {"vector": vector, "limit": limit, "with_payload": True}
        qdrant_filter = self._qdrant_filter(filters)
        if qdrant_filter:
            body["filter"] = qdrant_filter

        headers = {"api-key": self.settings.qdrant_api_key} if self.settings.qdrant_api_key else {}
        url = f"{qdrant['url'].rstrip('/')}/collections/{qdrant['collection']}/points/search"
        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            resp = await client.post(url, json=body, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        rows = []
        for hit in data.get("result", []):
            payload = hit.get("payload") or {}
            rows.append({**payload, "dense_score": hit.get("score"), "retrieval_source": "dense"})
        return rows

    def _bm25_search(
        self,
        query: str,
        limit: int,
        filters: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        chunks, bm25 = self.chunk_index.load()
        if not bm25:
            return []
        scores = bm25.get_scores(normalize_text(query).split())
        ranked = sorted(zip(chunks, scores), key=lambda pair: pair[1], reverse=True)
        rows = []
        for row, score in ranked:
            if score <= 0:
                continue
            if filters and not self._matches_filters(row, filters):
                continue
            rows.append({**row, "bm25_score": float(score), "retrieval_source": "bm25"})
            if len(rows) >= limit:
                break
        return rows

    @staticmethod
    def _fuse_candidates(*candidate_sets: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
        fused: dict[str, dict[str, Any]] = {}
        for candidates in candidate_sets:
            for rank, row in enumerate(candidates, start=1):
                key = row.get("chunk_id")
                if not key:
                    continue
                existing = fused.setdefault(key, row.copy())
                existing["rrf_score"] = existing.get("rrf_score", 0.0) + 1.0 / (60 + rank)
                for score_key in ("dense_score", "bm25_score"):
                    if score_key in row:
                        existing[score_key] = row[score_key]
                sources = set(existing.get("retrieval_sources", []))
                sources.add(row.get("retrieval_source", "unknown"))
                existing["retrieval_sources"] = sorted(sources)
        return sorted(fused.values(), key=lambda row: row.get("rrf_score", 0.0), reverse=True)[:limit]

    @staticmethod
    def _matches_filters(row: dict[str, Any], filters: dict[str, Any]) -> bool:
        for key, expected in filters.items():
            actual = row.get(key)
            if isinstance(expected, list):
                if actual not in expected:
                    return False
            elif actual != expected:
                return False
        return True

    @staticmethod
    def _qdrant_filter(filters: dict[str, Any] | None) -> dict[str, Any] | None:
        if not filters:
            return None
        must = []
        for key, expected in filters.items():
            if isinstance(expected, list):
                must.append({"key": key, "match": {"any": expected}})
            else:
                must.append({"key": key, "match": {"value": expected}})
        return {"must": must} if must else None


def format_retrieval_row(row: dict[str, Any], index: int | None = None) -> dict[str, Any]:
    scores = {
        key: row[key]
        for key in ("dense_score", "bm25_score", "rrf_score", "rerank_score")
        if key in row
    }
    formatted = {
        "citation_key": row.get("citation_key"),
        "title": row.get("title"),
        "source_path": row.get("source_path"),
        "relative_source_path": row.get("relative_source_path"),
        "chunk_id": row.get("chunk_id"),
        "scores": scores,
        "retrieval_sources": row.get("retrieval_sources", []),
        "snippet": snippet(row.get("text", "")),
    }
    if index is not None:
        formatted["index"] = index
    return formatted
