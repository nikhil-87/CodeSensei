"""Reusable in-memory fakes for the AI ports.

Lets every test in this folder swap the heavyweight Ollama / Chroma
clients for predictable stand-ins.
"""
from __future__ import annotations

import hashlib
import math
from collections.abc import Iterator, Sequence

from engine.ai.ports import ChatMessage, StoredChunk


class FakeEmbedder:
    """Deterministic 16-dim embedder driven by a SHA-256 hash.

    Two near-identical strings hash to similar-but-different vectors which
    is enough to validate ordering in retrieval tests.
    """

    DIM = 16

    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(tuple(texts))
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Map 16 bytes → 16 floats in [-1, 1].
        floats = [(b - 128) / 128.0 for b in digest[: self.DIM]]
        # L2-normalise so cosine similarity behaves sensibly.
        norm = math.sqrt(sum(f * f for f in floats)) or 1.0
        return [f / norm for f in floats]


class FakeVectorStore:
    """In-memory vector store that ranks by cosine similarity."""

    def __init__(self) -> None:
        self.records: dict[str, dict[str, object]] = {}

    # ports.VectorStore interface ----------------------------------------
    def upsert(
        self,
        ids: Sequence[str],
        contents: Sequence[str],
        metadatas: Sequence[dict[str, str | int | float | bool]],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        for i, content, meta, vec in zip(
            ids, contents, metadatas, embeddings, strict=True
        ):
            self.records[i] = {
                "content": content,
                "metadata": dict(meta),
                "embedding": list(vec),
            }

    def query(
        self,
        embedding: Sequence[float],
        *,
        top_k: int,
        filter: dict[str, str | int | float | bool] | None = None,
    ) -> list[StoredChunk]:
        scored: list[tuple[float, str, dict[str, object]]] = []
        for chunk_id, rec in self.records.items():
            if filter and not all(rec["metadata"].get(k) == v for k, v in filter.items()):
                continue
            sim = _cosine(list(embedding), rec["embedding"])  # type: ignore[arg-type]
            scored.append((sim, chunk_id, rec))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[StoredChunk] = []
        for sim, chunk_id, rec in scored[:top_k]:
            out.append(
                StoredChunk(
                    chunk_id=chunk_id,
                    content=str(rec["content"]),
                    metadata=dict(rec["metadata"]),  # type: ignore[arg-type]
                    score=max(0.0, min(1.0, (sim + 1.0) / 2.0)),
                )
            )
        return out

    def delete_collection(self) -> None:
        self.records.clear()

    def count(self) -> int:
        return len(self.records)


class FakeStreamGenerator:
    """Yields a fixed token stream regardless of input."""

    def __init__(self, tokens: Sequence[str]) -> None:
        self._tokens = list(tokens)
        self.last_messages: list[ChatMessage] | None = None
        self.last_temperature: float | None = None

    def __call__(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> Iterator[str]:
        self.last_messages = list(messages)
        self.last_temperature = temperature
        yield from self._tokens


class FakeGenerator:
    """Returns a fixed string from a non-streaming chat call."""

    def __init__(self, response: str) -> None:
        self._response = response
        self.last_messages: list[ChatMessage] | None = None

    def __call__(
        self, messages: Sequence[ChatMessage], *, temperature: float = 0.2
    ) -> str:
        self.last_messages = list(messages)
        return self._response


# ---------------------------------------------------------------------------
def _cosine(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise AssertionError("dimension mismatch")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(x * x for x in b)) or 1.0
    return dot / (na * nb)
