"""Convenience builders that wire :class:`RagChain` from plain config.

The engine itself is settings-agnostic (Clean Architecture). Both the
worker and the backend SSE endpoint need to instantiate a chain from a
small bag of strings/ints — this module is the single source of truth
for that wiring so the two services stay consistent.

Supports multiple AI providers:
    - "ollama" — Local LLM via Ollama (requires 8GB+ RAM)
    - "groq" — Free cloud LLM API (requires GROQ_API_KEY)
    - "huggingface" — Free embeddings API (requires HF_API_KEY)
    - "local" — Local sentence-transformers embeddings (CPU-friendly)
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from engine.ai.ollama_client import OllamaClient, OllamaSettings
from engine.ai.rag_chain import RagChain, RagChainOptions
from engine.ai.vector_store import ChromaVectorStore, ChromaVectorStoreOptions
from engine import _defaults

# Type aliases for provider selection
LLMProvider = Literal["ollama", "groq"]
EmbeddingProvider = Literal["ollama", "huggingface", "local"]


@dataclass(frozen=True)
class AIRuntimeConfig:
    """Plain-data config that drives :func:`build_rag_chain`.

    Supports multiple providers for free-tier deployment:
        - llm_provider: "ollama" (local) or "groq" (free API)
        - embedding_provider: "ollama", "huggingface" (free API), or "local"
    
    All defaults are sourced from shared.config.defaults when available.
    """

    repository_id: str

    # Provider selection (defaults to Ollama for backward compatibility)
    llm_provider: LLMProvider = "ollama"
    embedding_provider: EmbeddingProvider = "ollama"

    # Ollama settings (used when provider is "ollama")
    ollama_base_url: str = _defaults.OLLAMA_BASE_URL
    ollama_chat_model: str = _defaults.OLLAMA_CHAT_MODEL
    ollama_embed_model: str = _defaults.OLLAMA_EMBED_MODEL
    ollama_timeout_seconds: float = float(_defaults.OLLAMA_TIMEOUT_SECONDS)

    # Groq settings (used when llm_provider is "groq")
    groq_api_key: str = ""
    groq_chat_model: str = _defaults.GROQ_CHAT_MODEL

    # HuggingFace settings (used when embedding_provider is "huggingface")
    huggingface_api_key: str = ""
    huggingface_embed_model: str = _defaults.HUGGINGFACE_EMBED_MODEL

    # Local embeddings (used when embedding_provider is "local")
    local_embed_model: str = _defaults.LOCAL_EMBED_MODEL

    # ChromaDB settings
    chroma_host: str = _defaults.CHROMA_HOST
    chroma_port: int = _defaults.CHROMA_PORT
    chroma_collection_prefix: str = _defaults.CHROMA_COLLECTION_PREFIX
    chroma_distance: str = _defaults.CHROMA_DISTANCE

    # RAG options
    embedding_batch_size: int = _defaults.AI_EMBEDDING_BATCH_SIZE


@dataclass
class AIRuntime:
    """Bundle returned by :func:`build_rag_chain`.

    Callers hold onto resources so they can close() them on shutdown.
    The ``ollama`` field is kept for backward compatibility but may be None
    when using cloud providers.
    """

    chain: RagChain
    ollama: OllamaClient | None  # None when using Groq
    vector_store: ChromaVectorStore

    # Additional resources that may need cleanup
    _embedding_client: object | None = None
    _llm_client: object | None = None

    def close(self) -> None:
        """Close all owned resources."""
        if self.ollama is not None:
            try:
                self.ollama.close()
            except Exception:
                pass
        if self._embedding_client is not None and hasattr(self._embedding_client, "close"):
            try:
                self._embedding_client.close()
            except Exception:
                pass
        if self._llm_client is not None and hasattr(self._llm_client, "close"):
            try:
                self._llm_client.close()
            except Exception:
                pass


def build_rag_chain(config: AIRuntimeConfig) -> AIRuntime:
    """Construct a fully-wired :class:`RagChain` from ``config``.

    Supports multiple providers:
        - Ollama (local LLM) — default, requires local Ollama server
        - Groq (free cloud API) — set llm_provider="groq" and groq_api_key
        - HuggingFace embeddings — set embedding_provider="huggingface"
        - Local embeddings — set embedding_provider="local" (CPU-friendly)

    The returned runtime owns resources; call close() when done.
    """
    ollama_client: OllamaClient | None = None
    embedding_client: object | None = None
    llm_client: object | None = None
    embedding_fn = None
    generation_stream_fn = None

    # --- Build embedding function ---
    if config.embedding_provider == "ollama":
        # Use Ollama for embeddings (requires local server)
        if ollama_client is None:
            ollama_client = OllamaClient(
                OllamaSettings(
                    base_url=config.ollama_base_url,
                    chat_model=config.ollama_chat_model,
                    embed_model=config.ollama_embed_model,
                    request_timeout_seconds=config.ollama_timeout_seconds,
                )
            )
        embedding_fn = ollama_client.embed

    elif config.embedding_provider == "huggingface":
        # Use free HuggingFace Inference API
        from engine.ai.free_embeddings import (
            HuggingFaceEmbeddings,
            HuggingFaceSettings,
        )

        if not config.huggingface_api_key:
            raise ValueError(
                "huggingface_api_key required when embedding_provider='huggingface'. "
                "Get a free token at https://huggingface.co/settings/tokens"
            )
        hf_client = HuggingFaceEmbeddings(
            HuggingFaceSettings(
                api_key=config.huggingface_api_key,
                model=config.huggingface_embed_model,
            )
        )
        embedding_client = hf_client
        embedding_fn = hf_client.embed

    elif config.embedding_provider == "local":
        # Use local sentence-transformers (CPU-friendly, no API)
        from engine.ai.free_embeddings import LocalSentenceTransformerEmbeddings

        local_emb = LocalSentenceTransformerEmbeddings(model_name=config.local_embed_model)
        embedding_client = local_emb
        embedding_fn = local_emb.embed

    else:
        raise ValueError(f"Unknown embedding_provider: {config.embedding_provider}")

    # --- Build generation function ---
    if config.llm_provider == "ollama":
        # Use Ollama for LLM (requires local server)
        if ollama_client is None:
            ollama_client = OllamaClient(
                OllamaSettings(
                    base_url=config.ollama_base_url,
                    chat_model=config.ollama_chat_model,
                    embed_model=config.ollama_embed_model,
                    request_timeout_seconds=config.ollama_timeout_seconds,
                )
            )
        generation_stream_fn = ollama_client.stream_chat

    elif config.llm_provider == "groq":
        # Use free Groq API
        from engine.ai.groq_client import GroqClient, GroqSettings

        if not config.groq_api_key:
            raise ValueError(
                "groq_api_key required when llm_provider='groq'. "
                "Get a free key at https://console.groq.com/keys"
            )
        groq = GroqClient(
            GroqSettings(
                api_key=config.groq_api_key,
                chat_model=config.groq_chat_model,
            )
        )
        llm_client = groq
        generation_stream_fn = groq.stream_chat

    else:
        raise ValueError(f"Unknown llm_provider: {config.llm_provider}")

    # --- Build vector store ---
    store = ChromaVectorStore(
        ChromaVectorStoreOptions(
            host=config.chroma_host,
            port=config.chroma_port,
            collection_prefix=config.chroma_collection_prefix,
            repository_id=config.repository_id,
            distance=config.chroma_distance,
        )
    )

    # --- Build RAG chain ---
    chain = RagChain(
        vector_store=store,
        embedding_fn=embedding_fn,
        generation_stream_fn=generation_stream_fn,
        options=RagChainOptions(embedding_batch_size=config.embedding_batch_size),
    )

    return AIRuntime(
        chain=chain,
        ollama=ollama_client,
        vector_store=store,
        _embedding_client=embedding_client,
        _llm_client=llm_client,
    )

