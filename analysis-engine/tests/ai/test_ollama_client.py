"""Tests for :class:`engine.ai.OllamaClient` using a stubbed httpx transport."""
from __future__ import annotations

import json

import httpx
import pytest

from engine.ai.errors import EmbeddingError, GenerationError
from engine.ai.ollama_client import OllamaClient, OllamaSettings
from engine.ai.ports import ChatMessage


def _client(handler) -> OllamaClient:  # type: ignore[no-untyped-def]
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="http://ollama")
    return OllamaClient(OllamaSettings(base_url="http://ollama"), http_client=http)


def test_embed_returns_vectors_for_each_text() -> None:
    counter = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/embeddings"
        body = json.loads(request.content)
        assert body["model"] == "nomic-embed-text"
        counter["n"] += 1
        return httpx.Response(200, json={"embedding": [0.1, 0.2, 0.3]})

    with _client(handler) as client:
        vectors = client.embed(["a", "b", "c"])

    assert len(vectors) == 3
    assert counter["n"] == 3
    assert vectors[0] == [0.1, 0.2, 0.3]


def test_embed_raises_when_response_lacks_embedding() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"error": "no model"})

    with _client(handler) as client:
        with pytest.raises(EmbeddingError):
            client.embed(["a"])


def test_chat_returns_message_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is False
        return httpx.Response(
            200, json={"message": {"role": "assistant", "content": "hi there"}}
        )

    with _client(handler) as client:
        out = client.chat([ChatMessage(role="user", content="hi")])
    assert out == "hi there"


def test_stream_chat_yields_only_non_empty_tokens() -> None:
    lines = [
        json.dumps({"message": {"role": "assistant", "content": "Hello"}, "done": False}),
        json.dumps({"message": {"role": "assistant", "content": ""}, "done": False}),
        "not-json",  # malformed line is ignored, not raised
        json.dumps({"message": {"role": "assistant", "content": " world"}, "done": False}),
        json.dumps({"message": {"role": "assistant", "content": ""}, "done": True}),
    ]
    body = ("\n".join(lines) + "\n").encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    with _client(handler) as client:
        tokens = list(client.stream_chat([ChatMessage(role="user", content="hi")]))

    assert tokens == ["Hello", " world"]


def test_chat_raises_generation_error_on_http_failure() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    with _client(handler) as client:
        with pytest.raises(GenerationError):
            client.chat([ChatMessage(role="user", content="hi")])
