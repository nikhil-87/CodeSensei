"""LLM-augmented documentation writer.

The Phase-2 :class:`backend.app.services.documentation.DocumentationService`
already produces deterministic doc bodies from analysis facts. This class
takes those same facts plus retrieved code excerpts and asks the LLM to
turn them into a polished prose document. The backend's docs endpoint
will fall back to the deterministic version if the AI engine is offline.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import structlog

from engine.ai.errors import GenerationError
from engine.ai.ports import (
    EmbeddingFunction,
    GenerationFunction,
    StoredChunk,
    VectorStore,
)
from engine.ai.prompts import build_documentation_messages
from engine import _defaults

logger = structlog.get_logger(__name__)


DocKind = Literal[
    "readme",
    "architecture",
    "onboarding",
    "api",
    "technical_design",
    "summary",
]


@dataclass(frozen=True, slots=True)
class GeneratedDocument:
    """A rendered document, plus the citations that informed it."""

    kind: DocKind
    body_markdown: str
    citations: tuple[StoredChunk, ...]


_RETRIEVAL_QUERY: dict[DocKind, str] = {
    "readme": "high-level project purpose, entry points, and primary modules",
    "architecture": "module boundaries, layer interactions, and key abstractions",
    "onboarding": "how a new contributor sets up, builds, tests, and contributes",
    "api": "public endpoints, request/response schemas, and authentication",
    "technical_design": "core design decisions, data model, and trade-offs",
    "summary": "what the project does and how it is structured",
}


class LlmDocumentationWriter:
    """Generates Markdown documentation grounded in retrieval."""

    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_fn: EmbeddingFunction,
        generation_fn: GenerationFunction,
        retrieval_top_k: int = _defaults.AI_DOC_RETRIEVAL_TOP_K,
    ) -> None:
        self._vector_store = vector_store
        self._embed = embedding_fn
        self._generate = generation_fn
        self._top_k = retrieval_top_k

    def generate(
        self,
        *,
        kind: DocKind,
        repo_summary: str,
    ) -> GeneratedDocument:
        """Render a document of the given ``kind``.

        ``repo_summary`` is a short paragraph of analysis facts (file
        counts, languages, top symbols, …) the backend assembles before
        calling us.
        """
        retrieval_query = _RETRIEVAL_QUERY[kind]
        try:
            vectors = self._embed([retrieval_query])
        except Exception as exc:  # noqa: BLE001
            raise GenerationError(f"doc embedding failed: {exc}") from exc
        if not vectors:
            raise GenerationError("doc embedding returned no vectors")
        retrieved = self._vector_store.query(vectors[0], top_k=self._top_k)

        messages = build_documentation_messages(
            kind=kind,
            repo_summary=repo_summary,
            retrieved=retrieved,
        )
        body = self._generate(messages, temperature=0.2)
        return GeneratedDocument(
            kind=kind,
            body_markdown=body.strip(),
            citations=tuple(retrieved),
        )

    @staticmethod
    def supported_kinds() -> Sequence[DocKind]:
        return tuple(_RETRIEVAL_QUERY.keys())
