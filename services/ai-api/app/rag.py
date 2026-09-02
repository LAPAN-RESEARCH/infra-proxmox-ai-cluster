from __future__ import annotations

from typing import Any

from .retrieval import format_retrieval_row
from .schemas import ChatMessage


def content_to_text(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text":
                    parts.append(str(item.get("text", "")))
                elif "text" in item:
                    parts.append(str(item["text"]))
            else:
                parts.append(str(item))
        return "\n".join(part for part in parts if part)
    return str(content)


def latest_user_query(messages: list[ChatMessage]) -> str:
    for message in reversed(messages):
        if message.role == "user":
            query = content_to_text(message.content).strip()
            if query:
                return query
    raise ValueError("RAG requires at least one non-empty user message")


def build_context(rows: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    blocks = [
        "Use the retrieved context below when it is relevant. Cite sources with bracketed numbers such as [1]. "
        "If the context does not contain enough evidence, say what is missing."
    ]
    citations = []
    for index, row in enumerate(rows, start=1):
        title = row.get("title") or "Untitled"
        citation_key = row.get("citation_key") or row.get("chunk_id") or f"source-{index}"
        chunk_id = row.get("chunk_id") or ""
        blocks.append(
            f"\n[{index}] citation_key={citation_key}; title={title}; chunk_id={chunk_id}\n"
            f"{row.get('text', '').strip()}"
        )
        citations.append(format_retrieval_row(row, index=index))
    return "\n".join(blocks), citations


def messages_for_ollama(messages: list[dict[str, Any]]) -> list[dict[str, str]]:
    mapped = []
    for message in messages:
        role = message.get("role", "user")
        if role == "developer":
            role = "system"
        if role not in {"system", "user", "assistant", "tool"}:
            role = "user"
        mapped.append({"role": role, "content": content_to_text(message.get("content"))})
    return mapped


def build_ollama_options(request_data: dict[str, Any]) -> dict[str, Any]:
    options: dict[str, Any] = {}
    if request_data.get("temperature") is not None:
        options["temperature"] = request_data["temperature"]
    if request_data.get("top_p") is not None:
        options["top_p"] = request_data["top_p"]
    if request_data.get("max_tokens") is not None:
        options["num_predict"] = request_data["max_tokens"]
    if request_data.get("stop") is not None:
        options["stop"] = request_data["stop"]
    return options


def build_chat_payload(model: str, messages: list[dict[str, Any]], request_data: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages_for_ollama(messages),
    }
    options = build_ollama_options(request_data)
    if options:
        payload["options"] = options

    response_format = request_data.get("response_format")
    if isinstance(response_format, dict) and response_format.get("type") == "json_object":
        payload["format"] = "json"
    elif isinstance(response_format, dict) and response_format.get("type") == "json_schema":
        schema = response_format.get("json_schema", {}).get("schema")
        payload["format"] = schema or "json"
    return payload
