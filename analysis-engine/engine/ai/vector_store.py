"""ChromaDB-backed implementation of :class:`engine.ai.ports.VectorStore`.

We import ``chromadb`` lazily so the engine still imports without it
installed (devs running ``pytest`` on the parsers only). The collection
name encodes the repository ID so different repositories never share a
namespace.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import structlog

from engine.ai.errors import VectorStoreError
from engine.ai.ports import StoredChunk
from engine import _defaults

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class ChromaVectorStoreOptions:
    """Connection + collection knobs."""

    host: str = _defaults.CHROMA_HOST
    port: int = _defaults.CHROMA_PORT
    collection_prefix: str = _defaults.CHROMA_COLLECTION_PREFIX
    repository_id: str = "default"
    distance: str = _defaults.CHROMA_DISTANCE  # cosine | l2 | ip


class ChromaVectorStore:
    """Thin wrapper translating :class:`VectorStore` calls into Chroma calls."""

    def __init__(
        self,
        options: ChromaVectorStoreOptions | None = None,
        *,
        client: Any | None = None,
    ) -> None:
        self._options = options or ChromaVectorStoreOptions()
        self._collection_name = f"{self._options.collection_prefix}{self._options.repository_id}"
        self._client: Any | None = client
        self._collection: Any | None = None

    # ------------------------------------------------------------------
    # VectorStore protocol
    # ------------------------------------------------------------------
    def upsert(
        self,
        ids: Sequence[str],
        contents: Sequence[str],
        metadatas: Sequence[dict[str, str | int | float | bool]],
        embeddings: Sequence[Sequence[float]],
    ) -> None:
        if not ids:
            return
        if not (len(ids) == len(contents) == len(metadatas) == len(embeddings)):
            raise VectorStoreError(
                "upsert: ids/contents/metadatas/embeddings must be the same length"
            )
        try:
            self._get_collection().upsert(
                ids=list(ids),
                documents=list(contents),
                metadatas=[dict(m) for m in metadatas],
                embeddings=[list(e) for e in embeddings],
            )
        except Exception as exc:  # noqa: BLE001 — Chroma raises many shapes
            raise VectorStoreError(f"Chroma upsert failed: {exc}") from exc

    def query(
        self,
        embedding: Sequence[float],
        *,
        top_k: int,
        filter: dict[str, str | int | float | bool] | None = None,
    ) -> list[StoredChunk]:
        try:
            raw = self._get_collection().query(
                query_embeddings=[list(embedding)],
                n_results=max(1, top_k),
                where=dict(filter) if filter else None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Chroma query failed: {exc}") from exc

        ids = (raw.get("ids") or [[]])[0]
        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]

        out: list[StoredChunk] = []
        for chunk_id, content, metadata, distance in zip(
            ids, docs, metas, distances, strict=False
        ):
            score = _distance_to_score(self._options.distance, float(distance))
            out.append(
                StoredChunk(
                    chunk_id=str(chunk_id),
                    content=str(content or ""),
                    metadata=dict(metadata or {}),
                    score=score,
                )
            )
        return out

    def delete_collection(self) -> None:
        try:
            self._get_client().delete_collection(self._collection_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "chroma_delete_failed", collection=self._collection_name, error=str(exc)
            )
        self._collection = None

    def count(self) -> int:
        try:
            return int(self._get_collection().count())
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(f"Chroma count failed: {exc}") from exc

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            import chromadb  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover
            raise VectorStoreError(
                "chromadb is not installed; install with `pip install chromadb`"
            ) from exc
        self._client = chromadb.HttpClient(
            host=self._options.host, port=self._options.port
        )
        return self._client

    def _get_collection(self) -> Any:
        if self._collection is not None:
            return self._collection
        client = self._get_client()
        try:
            self._collection = client.get_or_create_collection(
                name=self._collection_name,
                metadata={"hnsw:space": self._options.distance},
            )
        except Exception as exc:  # noqa: BLE001
            raise VectorStoreError(
                f"Chroma get_or_create_collection failed: {exc}"
            ) from exc
        return self._collection


def _distance_to_score(distance_kind: str, distance: float) -> float:
    """Convert Chroma's distance into a 0..1 similarity score.

    Chroma stores ``cosine`` as ``1 - cosine_similarity`` and ``l2`` as
    squared L2. We normalise to a "higher is better" 0..1 scale that
    callers can use for ranking + thresholding.
    """
    if distance_kind == "cosine":
        return max(0.0, min(1.0, 1.0 - distance))
    if distance_kind == "l2":
        # 1 / (1 + d) is monotone-decreasing in d, in (0, 1].
        return 1.0 / (1.0 + max(0.0, distance))
    if distance_kind == "ip":
        # Inner-product: Chroma returns negative IP, so flip + clip.
        return max(0.0, min(1.0, -distance))
    return max(0.0, 1.0 - distance)
