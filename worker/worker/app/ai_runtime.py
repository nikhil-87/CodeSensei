"""Helpers for spinning up the AI engine inside a worker process.

The worker uses the engine's :func:`build_rag_chain` factory but adds:
* graceful degradation if Ollama / Chroma are unreachable (we *log* and
  skip indexing rather than failing the whole analysis job),
* a tiny helper for reading the cloned repo's source files into memory
  for chunking.
"""
from __future__ import annotations

import uuid
from collections.abc import Iterable
from pathlib import Path

import structlog

from engine.ai import (
    AIRuntime,
    AIRuntimeConfig,
    IndexingResult,
    build_rag_chain,
)
from engine.ai.errors import AIError
from engine.results import FileAnalysis
from worker.app.exceptions import IndexingDegraded
from worker.app.settings import WorkerSettings

logger = structlog.get_logger(__name__)


def build_runtime(settings: WorkerSettings, repository_id: uuid.UUID) -> AIRuntime:
    """Construct a :class:`AIRuntime` for ``repository_id``."""
    config = AIRuntimeConfig(
        repository_id=str(repository_id),
        # Provider selection — without this the engine defaults to Ollama
        # and indexing fails wherever Ollama isn't running.
        llm_provider=settings.llm_provider,
        embedding_provider=settings.embedding_provider,
        ollama_base_url=settings.ollama_base_url,
        ollama_chat_model=settings.ollama_chat_model,
        ollama_embed_model=settings.ollama_embed_model,
        ollama_timeout_seconds=float(settings.ollama_timeout_seconds),
        # Groq (free cloud LLM)
        groq_api_key=settings.groq_api_key,
        groq_chat_model=settings.groq_chat_model,
        # HuggingFace (free cloud embeddings)
        huggingface_api_key=settings.huggingface_api_key,
        huggingface_embed_model=settings.huggingface_embed_model,
        # Local embeddings (CPU-friendly fallback)
        local_embed_model=settings.local_embed_model,
        chroma_host=settings.chroma_host,
        chroma_port=settings.chroma_port,
        chroma_collection_prefix=settings.chroma_collection_prefix,
    )
    return build_rag_chain(config)


def read_sources(
    workspace: Path,
    files: Iterable[FileAnalysis],
    *,
    max_bytes_per_file: int = 2_000_000,
) -> dict[str, str]:
    """Read each file's text from disk for indexing.

    The chunker needs the raw source. We read lazily here rather than
    holding source in memory throughout analysis to keep peak RSS down.
    """
    out: dict[str, str] = {}
    for file in files:
        path = workspace / file.path
        if not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size > max_bytes_per_file:
            continue
        try:
            out[file.path] = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning(
                "ai_read_source_failed", path=file.path, error=str(exc)
            )
            continue
    return out


def index_with_runtime(
    runtime: AIRuntime,
    *,
    repository_id: uuid.UUID,
    files: Iterable[FileAnalysis],
    sources: dict[str, str],
) -> IndexingResult:
    """Run :meth:`RagChain.index_repository` and translate failures.

    Indexing is best-effort: AI infrastructure being down should *not* fail
    the analysis job. We raise :class:`IndexingDegraded` so the caller can
    log and continue.
    """
    try:
        # Wipe the prior collection so re-runs don't accumulate stale chunks.
        try:
            runtime.vector_store.delete_collection()
        except Exception as exc:  # noqa: BLE001
            logger.info("ai_delete_prev_collection_skipped", error=str(exc))

        return runtime.chain.index_repository(list(files), sources=sources)
    except AIError as exc:
        logger.warning(
            "ai_indexing_failed", repository_id=str(repository_id), error=str(exc)
        )
        raise IndexingDegraded(str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "ai_indexing_unexpected_error",
            repository_id=str(repository_id),
            error=str(exc),
        )
        raise IndexingDegraded(str(exc)) from exc
