"""HTTP client for Groq's free LLM API.

Groq provides free access to fast LLM inference with generous rate limits.
This is an alternative to Ollama for cloud deployments where running
local LLMs isn't practical.

Free tier includes:
    - 30 requests/minute for most models
    - llama-3.3-70b-versatile (best for code)
    - llama-3.1-8b-instant (faster, smaller)
    - mixtral-8x7b-32768 (good for code)

Requires: GROQ_API_KEY environment variable or passed to constructor.

Note: Groq does NOT provide embeddings API. Use a free embedding service:
    - HuggingFace Inference API (free tier)
    - Voyage AI (free tier)
    - Or use sentence-transformers locally (CPU-friendly)
"""
from __future__ import annotations

import json
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from engine.ai.errors import GenerationError
from engine.ai.ports import ChatMessage
from engine import _defaults

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class GroqSettings:
    """Configuration for :class:`GroqClient`."""

    api_key: str
    base_url: str = _defaults.GROQ_BASE_URL
    chat_model: str = _defaults.GROQ_CHAT_MODEL  # Best free model for code
    request_timeout_seconds: float = float(_defaults.GROQ_TIMEOUT_SECONDS)
    max_retries: int = _defaults.GROQ_MAX_RETRIES


class GroqClient:
    """Client for Groq's free LLM API (OpenAI-compatible)."""

    def __init__(
        self,
        settings: GroqSettings,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(
            base_url=self._settings.base_url,
            timeout=self._settings.request_timeout_seconds,
            headers={
                "Authorization": f"Bearer {self._settings.api_key}",
                "Content-Type": "application/json",
            },
        )
        self._owns_client = http_client is None

    def close(self) -> None:
        """Close the underlying HTTP client if we own it."""
        if self._owns_client:
            self._client.close()

    # ------------------------------------------------------------------
    # Chat — non-streaming
    # ------------------------------------------------------------------
    @retry(
        retry=retry_if_exception_type((httpx.HTTPError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    def chat(
        self,
        messages: Sequence[ChatMessage],
        *,
        temperature: float = 0.2,
    ) -> str:
        """Single round-trip chat completion via Groq."""
        try:
            response = self._client.post(
                "/chat/completions",
                json={
                    "model": self._settings.chat_model,
                    "messages": [
                        {"role": m.role, "content": m.content} for m in messages
                    ],
                    "temperature": float(temperature),
                    "stream": False,
                },
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc)
        except httpx.HTTPError as exc:
            raise GenerationError(f"Groq request failed: {exc}") from exc

        try:
            payload = response.json()
        except json.JSONDecodeError as exc:
            raise GenerationError(f"Groq returned non-JSON: {response.text!r}") from exc

        choices = payload.get("choices", [])
        if not choices:
            raise GenerationError(f"Groq returned no choices: {payload!r}")

        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str):
            raise GenerationError(f"Groq returned no message content: {payload!r}")
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
        """Yield content tokens as they arrive from Groq.

        Uses OpenAI-compatible SSE streaming format.
        """
        try:
            with self._client.stream(
                "POST",
                "/chat/completions",
                json={
                    "model": self._settings.chat_model,
                    "messages": [
                        {"role": m.role, "content": m.content} for m in messages
                    ],
                    "temperature": float(temperature),
                    "stream": True,
                },
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or line.startswith(":"):
                        continue
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc)
        except httpx.HTTPError as exc:
            raise GenerationError(f"Groq streaming failed: {exc}") from exc

    def _handle_http_error(self, exc: httpx.HTTPStatusError) -> None:
        """Translate HTTP errors to domain errors with helpful messages."""
        status = exc.response.status_code
        try:
            # The streaming path raises before the body is consumed, so we
            # must read it explicitly before touching ``.json()``/``.text``.
            if not exc.response.is_closed:
                exc.response.read()
            body = exc.response.json()
            error_msg = body.get("error", {}).get("message", str(exc))
        except Exception:
            error_msg = exc.response.text or str(exc)

        if status == 401:
            raise GenerationError(
                f"Groq API key invalid or missing. Get a free key at "
                f"https://console.groq.com/keys — Error: {error_msg}"
            ) from exc
        elif status == 429:
            raise GenerationError(
                f"Groq rate limit exceeded. Free tier: 30 req/min. "
                f"Wait a moment and retry. Error: {error_msg}"
            ) from exc
        elif status == 503:
            raise GenerationError(
                f"Groq service temporarily unavailable. Retry shortly. "
                f"Error: {error_msg}"
            ) from exc
        else:
            raise GenerationError(f"Groq API error ({status}): {error_msg}") from exc


# ---------------------------------------------------------------------------
# Helper: list available models (for diagnostics)
# ---------------------------------------------------------------------------
def list_groq_models(api_key: str) -> list[dict[str, Any]]:
    """Fetch list of available Groq models (useful for debugging)."""
    with httpx.Client(
        base_url="https://api.groq.com/openai/v1",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30.0,
    ) as client:
        response = client.get("/models")
        response.raise_for_status()
        return response.json().get("data", [])
