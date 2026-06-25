"""AI service — builds a :class:`RagChain` and adapts it to async SSE.

The chat endpoint runs in the API process, so we can't go through RQ
without paying serialisation latency. Instead this service constructs
the chain inline using the engine's :func:`build_rag_chain` factory and
wraps :meth:`RagChain.stream_chat` (a sync iterator) into an async
generator suitable for FastAPI / sse-starlette.
"""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator, Iterator
from typing import TYPE_CHECKING

import structlog

from app.core.config import Settings
from app.schemas.ai import ChatRequest as ApiChatRequest

if TYPE_CHECKING:
    from engine.ai import AIRuntime

logger = structlog.get_logger(__name__)


class AIService:
    """Bridges the AI engine into the API's async request handlers."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def stream_chat(
        self, request: ApiChatRequest
    ) -> AsyncIterator[dict[str, str]]:
        """Yield SSE-shaped dicts for ``EventSourceResponse``.

        The events conform to :class:`app.schemas.ai.ChatTokenEvent`.
        On any failure we yield a single ``error`` event followed by a
        ``done`` event so the frontend always sees a clean terminator.
        """
        runtime = self._build_runtime(request.repository_id)
        try:
            from engine.ai import ChatRequest as EngineChatRequest  # noqa: PLC0415
            from engine.ai.ports import ChatMessage  # noqa: PLC0415

            history = tuple(
                ChatMessage(role=m.role, content=m.content) for m in request.history
            )
            engine_request = EngineChatRequest(
                question=request.question,
                history=history,
                top_k=request.top_k,
                file_paths=tuple(request.attached_paths),
            )

            iterator = runtime.chain.stream_chat(engine_request)
            async for sse in _async_stream_events(iterator):
                yield sse
        finally:
            try:
                runtime.close()  # Use unified close() method
            except Exception:  # noqa: BLE001
                logger.debug("runtime_close_failed_silent")

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    def delete_repository_index(self, repository_id: uuid.UUID) -> None:
        """Best-effort removal of a repository's vector index.

        Deleting a repository cascades its Postgres rows, but the indexed source
        chunks live in a separate ChromaDB collection (``repo_<id>``). Without
        this, a deleted — possibly private — repository's code would remain
        retrievable from the vector store forever (a data-retention/privacy leak
        and unbounded storage growth). Failures are swallowed: the collection may
        not exist (repo never indexed) and cleanup must never block deletion.
        """
        try:
            from engine.ai import (  # noqa: PLC0415
                ChromaVectorStore,
                ChromaVectorStoreOptions,
            )

            s = self._settings
            store = ChromaVectorStore(
                ChromaVectorStoreOptions(
                    host=s.chroma_host,
                    port=s.chroma_port,
                    collection_prefix=s.chroma_collection_prefix,
                    repository_id=str(repository_id),
                )
            )
            store.delete_collection()
            logger.info("repository_index_deleted", repository_id=str(repository_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "repository_index_delete_failed",
                repository_id=str(repository_id),
                error=str(exc),
            )

    def _build_runtime(self, repository_id: uuid.UUID) -> "AIRuntime":
        # Imported lazily so the backend test suite doesn't need chromadb
        # installed for non-AI tests.
        from engine.ai import AIRuntimeConfig, build_rag_chain  # noqa: PLC0415

        s = self._settings
        config = AIRuntimeConfig(
            repository_id=str(repository_id),
            # Provider selection
            llm_provider=s.llm_provider,
            embedding_provider=s.embedding_provider,
            # Ollama settings
            ollama_base_url=s.ollama_base_url,
            ollama_chat_model=s.ollama_chat_model,
            ollama_embed_model=s.ollama_embed_model,
            ollama_timeout_seconds=float(s.ollama_timeout_seconds),
            # Groq settings (free cloud LLM)
            groq_api_key=s.groq_api_key,
            groq_chat_model=s.groq_chat_model,
            # HuggingFace settings (free cloud embeddings)
            huggingface_api_key=s.huggingface_api_key,
            huggingface_embed_model=s.huggingface_embed_model,
            # Local embeddings
            local_embed_model=s.local_embed_model,
            # ChromaDB
            chroma_host=s.chroma_host,
            chroma_port=s.chroma_port,
            chroma_collection_prefix=s.chroma_collection_prefix,
        )
        return build_rag_chain(config)


# ---------------------------------------------------------------------------
# Sync iterator → async generator over EventSourceResponse-shaped dicts
# ---------------------------------------------------------------------------
async def _async_stream_events(
    iterator: "Iterator",
) -> AsyncIterator[dict[str, str]]:
    """Run ``next(iterator)`` in a thread, yielding SSE dicts.

    Uses ``asyncio.to_thread`` so the event loop never blocks on either
    Ollama I/O or Chroma I/O. Translates engine ``ChatStreamEvent`` →
    backend ``ChatTokenEvent`` JSON.
    """
    from app.schemas.ai import ChatCitation, ChatTokenEvent  # noqa: PLC0415

    sentinel = object()

    def _next() -> object:
        try:
            return next(iterator)
        except StopIteration:
            return sentinel

    while True:
        item = await asyncio.to_thread(_next)
        if item is sentinel:
            return

        engine_event = item  # ChatStreamEvent
        if engine_event.event == "citations":
            citations = [
                ChatCitation(
                    file_path=c.file_path,
                    line_start=c.line_start,
                    line_end=c.line_end,
                    snippet="",
                )
                for c in (engine_event.citations or ())
            ]
            payload = ChatTokenEvent(event="citations", citations=citations)
            yield {"event": "citations", "data": payload.model_dump_json()}

        elif engine_event.event == "token":
            payload = ChatTokenEvent(event="token", content=engine_event.content)
            yield {"event": "token", "data": payload.model_dump_json()}

        elif engine_event.event == "done":
            payload = ChatTokenEvent(event="done")
            yield {"event": "done", "data": payload.model_dump_json()}
            return

        elif engine_event.event == "error":
            payload = ChatTokenEvent(event="error", error=engine_event.error)
            yield {"event": "error", "data": payload.model_dump_json()}
            done = ChatTokenEvent(event="done")
            yield {"event": "done", "data": done.model_dump_json()}
            return
