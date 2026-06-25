"""Free embedding providers for cloud deployment.

When running without local Ollama, we need external embeddings. Options:

1. HuggingFace Inference API (free tier, rate limited)
2. Voyage AI (free tier)
3. Local sentence-transformers (CPU-friendly, no API needed)

This module implements HuggingFace and local sentence-transformers.
"""
from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from engine.ai.errors import EmbeddingError
from engine import _defaults

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# HuggingFace Inference API (free tier)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class HuggingFaceSettings:
    """Configuration for HuggingFace Inference API embeddings."""

    api_key: str  # Get free at https://huggingface.co/settings/tokens
    model: str = _defaults.HUGGINGFACE_EMBED_MODEL  # Fast, small, free
    base_url: str = _defaults.HUGGINGFACE_BASE_URL
    request_timeout_seconds: float = float(_defaults.HUGGINGFACE_TIMEOUT_SECONDS)


class HuggingFaceEmbeddings:
    """Embeddings via HuggingFace free Inference API.

    Free tier includes:
        - Rate limited but generous for personal projects
        - sentence-transformers models work well
        - No GPU required on your side
    """

    def __init__(
        self,
        settings: HuggingFaceSettings,
        *,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._client = http_client or httpx.Client(
            base_url=self._settings.base_url,
            timeout=self._settings.request_timeout_seconds,
            headers={"Authorization": f"Bearer {self._settings.api_key}"},
        )
        self._owns_client = http_client is None

    def close(self) -> None:
        """Close the HTTP client if we own it."""
        if self._owns_client:
            self._client.close()

    @retry(
        retry=retry_if_exception_type((httpx.HTTPError,)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Return embedding vectors for input texts.

        HuggingFace Inference API can handle batches, but we process
        one at a time for better error handling and rate limit management.
        """
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        """Embed a single text via HuggingFace API."""
        url = f"/hf-inference/models/{self._settings.model}/pipeline/feature-extraction"

        try:
            response = self._client.post(
                url,
                json={"inputs": text, "options": {"wait_for_model": True}},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            self._handle_http_error(exc, text)
        except httpx.HTTPError as exc:
            logger.warning("huggingface_embed_failed", error=str(exc))
            raise EmbeddingError(f"HuggingFace request failed: {exc}") from exc

        try:
            result = response.json()
        except json.JSONDecodeError as exc:
            raise EmbeddingError(
                f"HuggingFace returned non-JSON: {response.text!r}"
            ) from exc

        # HuggingFace returns nested array for sentence-transformers
        # Shape: [[384 floats]] for single input
        if isinstance(result, list):
            if result and isinstance(result[0], list):
                # Nested: take first (mean pooling already done)
                embedding = result[0]
            else:
                embedding = result
        else:
            raise EmbeddingError(f"Unexpected HuggingFace response: {result!r}")

        if not embedding or not isinstance(embedding[0], (int, float)):
            raise EmbeddingError(f"Invalid embedding format: {result!r}")

        return [float(x) for x in embedding]

    def _handle_http_error(self, exc: httpx.HTTPStatusError, text: str) -> None:
        """Translate HTTP errors to domain errors."""
        status = exc.response.status_code
        try:
            body = exc.response.json()
            error_msg = body.get("error", str(exc))
        except Exception:
            error_msg = exc.response.text or str(exc)

        if status == 401:
            raise EmbeddingError(
                f"HuggingFace API token invalid. Get a free token at "
                f"https://huggingface.co/settings/tokens — Error: {error_msg}"
            ) from exc
        elif status == 429:
            raise EmbeddingError(
                f"HuggingFace rate limit exceeded. Wait and retry. "
                f"Error: {error_msg}"
            ) from exc
        elif status == 503:
            # Model loading — HF will load it, retry
            raise EmbeddingError(
                f"Model loading on HuggingFace. Retry in a few seconds. "
                f"Error: {error_msg}"
            ) from exc
        else:
            raise EmbeddingError(
                f"HuggingFace API error ({status}): {error_msg}"
            ) from exc


# ---------------------------------------------------------------------------
# Local sentence-transformers (no API, CPU-friendly)
# ---------------------------------------------------------------------------
class LocalSentenceTransformerEmbeddings:
    """CPU-friendly local embeddings using sentence-transformers.

    This is the best option for:
        - No API keys needed
        - Works offline
        - Low RAM usage (~500MB for small models)
        - Fast enough on CPU for personal projects

    Requires: pip install sentence-transformers
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        """Initialize the local embedding model.

        Args:
            model_name: HuggingFace model name. Recommended:
                - "all-MiniLM-L6-v2" — fast, 384 dims, ~80MB
                - "all-mpnet-base-v2" — better quality, 768 dims, ~420MB
        """
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers not installed. Run: "
                "pip install sentence-transformers"
            ) from exc

        self._model_name = model_name
        self._model = SentenceTransformer(model_name)
        logger.info("local_embeddings_loaded", model=model_name)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Compute embeddings locally (CPU-friendly)."""
        # sentence-transformers handles batching internally
        embeddings = self._model.encode(
            list(texts),
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return [emb.tolist() for emb in embeddings]

    def close(self) -> None:
        """No-op for local model."""
        pass
