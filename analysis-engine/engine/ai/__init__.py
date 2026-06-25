"""AI sub-package — RAG over a parsed repository.

Public surface
--------------
:class:`engine.ai.RagChain`               — orchestrator (index + query)
:class:`engine.ai.IndexingResult`         — return type of ``index_repository``
:class:`engine.ai.ChatRequest`            — query payload
:class:`engine.ai.ChatStreamEvent`        — yielded by ``stream_chat``
:class:`engine.ai.OllamaClient`           — chat + embed client (local)
:class:`engine.ai.GroqClient`             — chat client (free cloud API)
:class:`engine.ai.ChromaVectorStore`      — vector index implementation
:class:`engine.ai.CodeChunker`            — symbol-aware splitter
:class:`engine.ai.LlmDocumentationWriter` — LLM-augmented documentation
"""
from __future__ import annotations

from engine.ai.chunker import CodeChunk, CodeChunker, ChunkOptions
from engine.ai.documentation_writer import LlmDocumentationWriter
from engine.ai.errors import (
    AIError,
    EmbeddingError,
    GenerationError,
    VectorStoreError,
)
from engine.ai.factory import (
    AIRuntime,
    AIRuntimeConfig,
    EmbeddingProvider,
    LLMProvider,
    build_rag_chain,
)
from engine.ai.groq_client import GroqClient, GroqSettings
from engine.ai.ollama_client import OllamaClient, OllamaSettings
from engine.ai.ports import (
    ChatStreamEvent,
    EmbeddingFunction,
    GenerationFunction,
    GenerationStreamFunction,
    VectorStore,
)
from engine.ai.rag_chain import (
    ChatCitation,
    ChatRequest,
    IndexingResult,
    RagChain,
    RagChainOptions,
)
from engine.ai.vector_store import ChromaVectorStore, ChromaVectorStoreOptions

__all__ = [
    "AIError",
    "AIRuntime",
    "AIRuntimeConfig",
    "ChatCitation",
    "ChatRequest",
    "ChatStreamEvent",
    "ChromaVectorStore",
    "ChromaVectorStoreOptions",
    "ChunkOptions",
    "CodeChunk",
    "CodeChunker",
    "EmbeddingError",
    "EmbeddingFunction",
    "GenerationError",
    "GenerationFunction",
    "GenerationStreamFunction",
    "IndexingResult",
    "LlmDocumentationWriter",
    "OllamaClient",
    "OllamaSettings",
    "RagChain",
    "RagChainOptions",
    "VectorStore",
    "VectorStoreError",
    "build_rag_chain",
]
