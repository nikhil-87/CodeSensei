"""Errors raised by the AI sub-package."""
from __future__ import annotations

from engine.exceptions import EngineError


class AIError(EngineError):
    """Base class for every AI-engine failure."""


class EmbeddingError(AIError):
    """Embedding model returned an error or invalid response."""


class GenerationError(AIError):
    """Chat / completion model returned an error."""


class VectorStoreError(AIError):
    """ChromaDB (or test stand-in) failed."""
