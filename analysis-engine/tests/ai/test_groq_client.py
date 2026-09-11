"""Tests for :class:`engine.ai.GroqClient` using a stubbed httpx transport."""
from __future__ import annotations

import json

import httpx
import pytest

from engine.ai.errors import GenerationError
from engine.ai.groq_client import GroqClient, GroqSettings
from engine.ai.ports import ChatMessage


def _client(handler) -> GroqClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, base_url="https://api.groq.com/openai/v1")
    return GroqClient(
        GroqSettings(api_key="test-key", chat_model="openai/gpt-oss-120b"),
        http_client=http,
    )


def test_chat_returns_message_content() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["model"] == "openai/gpt-oss-120b"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"role": "assistant", "content": "hello from groq"}}
                ]
            },
        )

    with _client(handler) as client:
        out = client.chat([ChatMessage(role="user", content="hi")])
    assert out == "hello from groq"


def test_stream_chat_yields_tokens() -> None:
    lines = [
        "data: " + json.dumps({"choices": [{"delta": {"content": "Hello"}}]}),
        ": keep-alive comment",
        "data: " + json.dumps({"choices": [{"delta": {"content": " world"}}]}),
        "data: [DONE]",
    ]
    body = ("\n\n".join(lines) + "\n\n").encode("utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=body)

    with _client(handler) as client:
        tokens = list(client.stream_chat([ChatMessage(role="user", content="hi")]))

    assert tokens == ["Hello", " world"]


def test_stream_chat_handles_404_model_not_found() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            404,
            json={"error": {"message": "The model `llama-3.3-70b-versatile` does not exist"}},
        )

    with _client(handler) as client:
        with pytest.raises(GenerationError) as exc_info:
            list(client.stream_chat([ChatMessage(role="user", content="hi")]))

    assert "not found or deprecated" in str(exc_info.value)
    assert "GROQ_CHAT_MODEL" in str(exc_info.value)


def test_stream_chat_handles_401_invalid_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            401,
            json={"error": {"message": "Invalid API key"}},
        )

    with _client(handler) as client:
        with pytest.raises(GenerationError) as exc_info:
            list(client.stream_chat([ChatMessage(role="user", content="hi")]))

    assert "Groq API key invalid or missing" in str(exc_info.value)
