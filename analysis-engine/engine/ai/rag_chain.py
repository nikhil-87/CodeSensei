"""End-to-end RAG orchestrator.

Holds two flows:

* :meth:`RagChain.index_repository` — chunk the parsed files, embed them
  in batches, and upsert into the vector store. Idempotent: re-running on
  the same repository overwrites existing vectors with the same chunk_id.
* :meth:`RagChain.stream_chat` — answer a user question by retrieving
  top-k chunks, building a prompt, and streaming tokens from the LLM.
  Yields :class:`ChatStreamEvent` matching the backend SSE schema.

This module is **pure orchestration**. All I/O (HTTP, DB, vector store)
goes through ports, which lets the tests inject fakes.
"""
from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

from engine.ai.chunker import ChunkOptions, CodeChunk, CodeChunker
from engine.ai.errors import AIError, EmbeddingError, GenerationError
from engine.ai.ports import (
    ChatCitationLite,
    ChatMessage,
    ChatStreamEvent,
    EmbeddingFunction,
    GenerationStreamFunction,
    StoredChunk,
    VectorStore,
)
from engine.ai.prompts import build_chat_messages
from engine import _defaults

if TYPE_CHECKING:
    from engine.results import FileAnalysis

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class ChatCitation:
    """Public citation form returned to API callers."""

    chunk_id: str
    file_path: str
    line_start: int
    line_end: int
    language: str | None
    symbol_name: str | None
    score: float
    excerpt: str


@dataclass(frozen=True, slots=True)
class ChatRequest:
    """A user-facing chat query."""

    question: str
    history: tuple[ChatMessage, ...] = ()
    top_k: int = _defaults.AI_TOP_K_CHUNKS
    temperature: float = _defaults.AI_TEMPERATURE
    min_score: float = _defaults.AI_MIN_SCORE
    # Files the user explicitly tagged ("Ask AI about this file"). When set,
    # their chunks are retrieved by metadata filter and guaranteed a place in
    # the context, so a question about a tagged file is answered from that file
    # rather than from whatever happened to be vector-similar.
    file_paths: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class IndexingResult:
    """Return value of :meth:`RagChain.index_repository`."""

    chunks_indexed: int
    files_indexed: int
    files_skipped: int


@dataclass(frozen=True)
class RagChainOptions:
    """Knobs surfaced for tuning."""

    embedding_batch_size: int = _defaults.AI_EMBEDDING_BATCH_SIZE
    chunk_options: ChunkOptions = field(default_factory=ChunkOptions)


class RagChain:
    """Coordinates chunking, embedding, retrieval, and generation."""

    def __init__(
        self,
        *,
        vector_store: VectorStore,
        embedding_fn: EmbeddingFunction,
        generation_stream_fn: GenerationStreamFunction,
        chunker: CodeChunker | None = None,
        options: RagChainOptions | None = None,
    ) -> None:
        self._vector_store = vector_store
        self._embed = embedding_fn
        self._stream = generation_stream_fn
        self._options = options or RagChainOptions()
        self._chunker = chunker or CodeChunker(self._options.chunk_options)

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------
    def index_repository(
        self,
        files: Sequence["FileAnalysis"],
        sources: dict[str, str],
    ) -> IndexingResult:
        """Chunk ``files``, embed each chunk, persist into the vector store."""
        files_indexed = 0
        files_skipped = 0
        for file in files:
            if file.path in sources and sources[file.path].strip():
                files_indexed += 1
            else:
                files_skipped += 1

        chunks = self._chunker.chunk_repository(files, sources)
        if not chunks:
            logger.info(
                "rag_index_no_chunks",
                files_indexed=files_indexed,
                files_skipped=files_skipped,
            )
            return IndexingResult(
                chunks_indexed=0,
                files_indexed=files_indexed,
                files_skipped=files_skipped,
            )

        batch_size = max(1, self._options.embedding_batch_size)
        for batch_start in range(0, len(chunks), batch_size):
            batch = chunks[batch_start : batch_start + batch_size]
            try:
                vectors = self._embed([c.content for c in batch])
            except Exception as exc:  # noqa: BLE001
                raise EmbeddingError(f"Embedding batch failed: {exc}") from exc
            if len(vectors) != len(batch):
                raise EmbeddingError(
                    f"Expected {len(batch)} embeddings, got {len(vectors)}"
                )
            self._vector_store.upsert(
                ids=[c.chunk_id for c in batch],
                contents=[c.content for c in batch],
                metadatas=[_chunk_metadata(c) for c in batch],
                embeddings=vectors,
            )

        logger.info(
            "rag_index_complete",
            chunks_indexed=len(chunks),
            files_indexed=files_indexed,
            files_skipped=files_skipped,
        )
        return IndexingResult(
            chunks_indexed=len(chunks),
            files_indexed=files_indexed,
            files_skipped=files_skipped,
        )

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------
    def retrieve(self, query: str, *, top_k: int = 8) -> list[StoredChunk]:
        """Embed ``query`` and return the ``top_k`` most similar chunks."""
        try:
            vectors = self._embed([query])
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(f"Embedding query failed: {exc}") from exc
        if not vectors:
            raise EmbeddingError("Embedding model returned no vectors for query")
        return self._vector_store.query(vectors[0], top_k=top_k)

    def retrieve_scoped(
        self,
        query: str,
        *,
        top_k: int = 8,
        file_paths: Sequence[str] = (),
    ) -> list[StoredChunk]:
        """Retrieve chunks, prioritising any explicitly tagged ``file_paths``.

        Without ``file_paths`` this is identical to :meth:`retrieve`. With them,
        each tagged file is queried by ``file_path`` metadata filter so its most
        query-relevant chunks are guaranteed into the context (roughly 60% of
        the budget), then general retrieval fills the rest. Total context size
        stays bounded by ``top_k`` — same as before — so prompts don't bloat.
        """
        if not file_paths:
            return self.retrieve(query, top_k=top_k)

        try:
            vectors = self._embed([query])
        except Exception as exc:  # noqa: BLE001
            raise EmbeddingError(f"Embedding query failed: {exc}") from exc
        if not vectors:
            raise EmbeddingError("Embedding model returned no vectors for query")
        qvec = vectors[0]

        # Reserve the majority of the budget for the tagged files.
        scoped_budget = max(1, (top_k * 3) // 5)
        seen: set[str] = set()
        merged: list[StoredChunk] = []

        for path in file_paths:
            if len(merged) >= scoped_budget:
                break
            for chunk in self._vector_store.query(
                qvec, top_k=scoped_budget, filter={"file_path": path}
            ):
                if chunk.chunk_id not in seen:
                    seen.add(chunk.chunk_id)
                    merged.append(chunk)
                    if len(merged) >= scoped_budget:
                        break

        # Fill the remaining budget with general, repo-wide retrieval.
        for chunk in self._vector_store.query(qvec, top_k=top_k):
            if len(merged) >= top_k:
                break
            if chunk.chunk_id not in seen:
                seen.add(chunk.chunk_id)
                merged.append(chunk)

        return merged[:top_k]


    def stream_chat(self, request: ChatRequest) -> Iterator[ChatStreamEvent]:
        """Run a full retrieve-then-generate flow, yielding stream events.

        Event order is: ``citations`` (single event) → many ``token`` →
        one ``done``. On failure a single ``error`` event is yielded.
        """
        try:
            retrieved = self.retrieve_scoped(
                request.question,
                top_k=request.top_k,
                file_paths=request.file_paths,
            )
        except AIError as exc:
            yield ChatStreamEvent(event="error", error=str(exc))
            return

        if request.min_score > 0:
            tagged = set(request.file_paths)
            # Never drop a chunk from a file the user explicitly tagged, even
            # if its similarity to the question is low ("explain this file" is
            # a generic query that scores poorly against code).
            retrieved = [
                c
                for c in retrieved
                if c.score >= request.min_score
                or str(c.metadata.get("file_path", "")) in tagged
            ]


        citations = tuple(_citation_lite(c) for c in retrieved)
        yield ChatStreamEvent(event="citations", citations=citations)

        messages = build_chat_messages(
            user_question=request.question,
            history=request.history,
            retrieved=retrieved,
        )
        try:
            for token in self._stream(messages, temperature=request.temperature):
                if token:
                    yield ChatStreamEvent(event="token", content=token)
        except GenerationError as exc:
            yield ChatStreamEvent(event="error", error=str(exc))
            return
        except Exception as exc:  # noqa: BLE001
            yield ChatStreamEvent(event="error", error=f"generation failed: {exc}")
            return

        yield ChatStreamEvent(event="done")

    # ------------------------------------------------------------------
    # Helpers exposed for the worker / API layer
    # ------------------------------------------------------------------
    @staticmethod
    def hydrate_citations(retrieved: Sequence[StoredChunk]) -> list[ChatCitation]:
        """Convert ``StoredChunk`` into the API's full :class:`ChatCitation`."""
        out: list[ChatCitation] = []
        for chunk in retrieved:
            md = chunk.metadata
            out.append(
                ChatCitation(
                    chunk_id=chunk.chunk_id,
                    file_path=str(md.get("file_path", "")),
                    line_start=int(md.get("line_start", 0) or 0),
                    line_end=int(md.get("line_end", 0) or 0),
                    language=_opt_str(md.get("language")),
                    symbol_name=_opt_str(md.get("symbol_name")),
                    score=chunk.score,
                    excerpt=chunk.content,
                )
            )
        return out


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _chunk_metadata(chunk: CodeChunk) -> dict[str, str | int | float | bool]:
    md: dict[str, str | int | float | bool] = {
        "file_path": chunk.file_path,
        "line_start": int(chunk.line_start),
        "line_end": int(chunk.line_end),
    }
    if chunk.language:
        md["language"] = chunk.language
    if chunk.symbol_name:
        md["symbol_name"] = chunk.symbol_name
    if chunk.symbol_kind:
        md["symbol_kind"] = chunk.symbol_kind
    return md


def _citation_lite(chunk: StoredChunk) -> ChatCitationLite:
    md = chunk.metadata
    return ChatCitationLite(
        file_path=str(md.get("file_path", "")),
        line_start=int(md.get("line_start", 0) or 0),
        line_end=int(md.get("line_end", 0) or 0),
        score=chunk.score,
    )


def _opt_str(value: object) -> str | None:
    if value is None or value == "":
        return None
    return str(value)
