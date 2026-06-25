"""AI sub-package ports — protocols every external dependency hides behind.

Tests substitute fakes; the worker injects production implementations.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Literal, Protocol


# ---------------------------------------------------------------------------
# Vector store
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class StoredChunk:
    """A chunk persisted in the vector store, with its similarity score."""

    chunk_id: str
    content: str
    metadata: dict[str, str | int | float | bool]
    score: float  # cosine similarity, 0..1 (higher = more similar)


class VectorStore(Protocol):
    """Pluggable vector index. Implemented by :class:`ChromaVectorStore`."""

    def upsert(
        self,
        ids: Sequence[str],
        contents: Sequence[str],
        metadatas: Sequence[dict[str, str | int | float | bool]],
        embeddings: Sequence[Sequence[float]],
    ) -> None: ...

    def query(
        self,
        embedding: Sequence[float],
        *,
        top_k: int,
        filter: dict[str, str | int | float | bool] | None = None,
    ) -> list[StoredChunk]: ...

    def delete_collection(self) -> None: ...

    def count(self) -> int: ...


# ---------------------------------------------------------------------------
# Embedding / generation functions
# ---------------------------------------------------------------------------
class EmbeddingFunction(Protocol):
    """Returns a vector for each text. Used both at index and query time."""

    def __call__(self, texts: Sequence[str]) -> list[list[float]]: ...


class GenerationFunction(Protocol):
    """Returns a single completion string for a list of chat messages."""

    def __call__(
        self, messages: Sequence["ChatMessage"], *, temperature: float = 0.2
    ) -> str: ...


class GenerationStreamFunction(Protocol):
    """Streams completion tokens for a list of chat messages."""

    def __call__(
        self, messages: Sequence["ChatMessage"], *, temperature: float = 0.2
    ) -> Iterator[str]: ...


# ---------------------------------------------------------------------------
# Chat surface
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One turn of a chat conversation."""

    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    """An event emitted by :meth:`RagChain.stream_chat`.

    The event taxonomy matches the backend's SSE schema verbatim so the
    backend can forward events without translation.
    """

    event: Literal["citations", "token", "done", "error"]
    content: str | None = None
    citations: tuple["ChatCitationLite", ...] | None = None
    error: str | None = None


@dataclass(frozen=True, slots=True)
class ChatCitationLite:
    """Lightweight citation form passed in stream events."""

    file_path: str
    line_start: int
    line_end: int
    score: float
