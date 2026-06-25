"""HTTP client for an Ollama server.

Wraps two endpoints:
    POST /api/embeddings  — single text → vector
    POST /api/chat        — chat messages → completion (streaming or not)

The client is **synchronous** (httpx.Client). The worker runs jobs on a
threadpool so async wouldn't buy us anything; tests benefit from the
simpler call shape.
"""
from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from engine.ai.errors import EmbeddingError, GenerationError
from engine.ai.ports import ChatMessage
from engine import _defaults

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class OllamaSettings:
    """Configuration for :class:`OllamaClient`."""

    base_url: str = _defaults.OLLAMA_BASE_URL
    chat_model: str = _defaults.OLLAMA_CHAT_MODEL
    embed_model: str = _defaults.OLLAMA_EMBED_MODEL
    request_timeout_seconds: float = float(_defaults.OLLAMA_TIMEOUT_SECONDS)
    max_retries: int = _defaults.OLLAMA_MAX_RETRIES


class OllamaClient:
    """Thin client around Ollama's HTTP API."""

    def __init__(
        self,
        settings: OllamaSettings | None = None,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings or OllamaSettings()
        self._client = http_client or httpx.Client(
            base_url=self._settings.base_url,
            timeout=self._settings.request_timeout_seconds,
        )
        self._owns_client = http_client is None

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return one embedding vector per input text.

        Ollama's ``/api/embeddings`` endpoint takes a single prompt; we
        call it once per text. For large indexes the worker batches at a
        higher level.
        """
        return [self._embed_one(t) for t in texts]

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def _embed_one(self, text: str) -> list[float]:
        try:
            response = self._client.post(
                "/api/embeddings",
                json={"model": self._settings.embed_model, "prompt": text},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("ollama_embed_failed", error=str(exc))
            raise

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise EmbeddingError(f"Ollama returned non-JSON: {response.text!r}") from exc

        embedding = payload.get("embedding")
        if not isinstance(embedding, list) or not embedding:
            raise EmbeddingError(f"Ollama returned no embedding: {payload!r}")
        return [float(x) for x in embedding]

    # ------------------------------------------------------------------
    # Chat — non-streaming
    # ------------------------------------------------------------------
    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
    ) -> str:
        """Single round-trip chat completion."""
        try:
            response = self._client.post(
                "/api/chat",
                json={
                    "model": self._settings.chat_model,
                    "messages": [
                        {"role": m.role, "content": m.content} for m in messages
                    ],
                    "stream": False,
                    "options": {"temperature": float(temperature)},
                },
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise GenerationError(f"Ollama chat failed: {exc}") from exc

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise GenerationError(f"Ollama returned non-JSON: {response.text!r}") from exc

        message = payload.get("message", {})
        content = message.get("content")
        if not isinstance(content, str):
            raise GenerationError(f"Ollama returned no message content: {payload!r}")
        return content

    # ------------------------------------------------------------------
    # Chat — streaming
    # ------------------------------------------------------------------
    def stream_chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
    ) -> Iterator[str]:
        """Yield content tokens as they arrive from Ollama.

        Ollama emits one JSON object per line with ``message.content`` set
        to the next chunk and ``done: true`` on the final line.
        """
        body = {
            "model": self._settings.chat_model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": True,
            "options": {"temperature": float(temperature)},
        }
        try:
            with self._client.stream("POST", "/api/chat", json=body) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line:
                        continue
                    try:
                        payload = json.loads(line)
                    except json.JSONDecodeError:
                        # Skip malformed lines rather than aborting the stream.
                        continue
                    msg = payload.get("message")
                    if isinstance(msg, dict):
                        token = msg.get("content")
                        if isinstance(token, str) and token:
                            yield token
                    if payload.get("done"):
                        return
        except httpx.HTTPError as exc:
            raise GenerationError(f"Ollama stream_chat failed: {exc}") from exc

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "OllamaClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
