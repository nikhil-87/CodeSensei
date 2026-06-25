"""Single bridge from the engine to the platform's centralized config.

The analysis engine is a decoupled library (Clean Architecture, its own
``pyproject``). When it runs as part of the platform — bundled into the
worker and backend images — ``shared.config.defaults`` is the single
authoritative source for every non-secret default value.

To avoid scattering hardcoded literals across the engine's value objects
(``OllamaSettings``, ``GroqSettings``, ``HuggingFaceSettings``,
``CloneOptions``, ``AnalysisOptions``, ...), every engine default is read
from this module. This is the *only* place in the engine that knows how to
reach the shared config, and the only place that carries a standalone
fallback (used when the engine is imported in isolation, e.g. unit tests
without the platform's ``shared`` package on ``PYTHONPATH``).
"""
from __future__ import annotations

try:
    from shared.config import defaults as _d

    # Ollama (local provider)
    OLLAMA_BASE_URL = _d.OLLAMA_BASE_URL
    OLLAMA_CHAT_MODEL = _d.OLLAMA_CHAT_MODEL
    OLLAMA_EMBED_MODEL = _d.OLLAMA_EMBED_MODEL
    OLLAMA_TIMEOUT_SECONDS = _d.OLLAMA_TIMEOUT_SECONDS
    OLLAMA_MAX_RETRIES = _d.OLLAMA_MAX_RETRIES

    # Groq (cloud LLM)
    GROQ_BASE_URL = _d.GROQ_BASE_URL
    GROQ_CHAT_MODEL = _d.GROQ_CHAT_MODEL
    GROQ_TIMEOUT_SECONDS = _d.GROQ_TIMEOUT_SECONDS
    GROQ_MAX_RETRIES = _d.GROQ_MAX_RETRIES

    # HuggingFace (cloud embeddings)
    HUGGINGFACE_BASE_URL = _d.HUGGINGFACE_BASE_URL
    HUGGINGFACE_EMBED_MODEL = _d.HUGGINGFACE_EMBED_MODEL
    HUGGINGFACE_TIMEOUT_SECONDS = _d.HUGGINGFACE_TIMEOUT_SECONDS
    HUGGINGFACE_MAX_RETRIES = _d.HUGGINGFACE_MAX_RETRIES

    # Local embeddings
    LOCAL_EMBED_MODEL = _d.LOCAL_EMBED_MODEL

    # ChromaDB
    CHROMA_HOST = _d.CHROMA_HOST
    CHROMA_PORT = _d.CHROMA_PORT
    CHROMA_COLLECTION_PREFIX = _d.CHROMA_COLLECTION_PREFIX
    CHROMA_DISTANCE = _d.CHROMA_DISTANCE

    # RAG / embedding
    AI_EMBEDDING_BATCH_SIZE = _d.AI_EMBEDDING_BATCH_SIZE
    AI_TOP_K_CHUNKS = _d.AI_TOP_K_CHUNKS
    AI_TEMPERATURE = _d.AI_TEMPERATURE
    AI_MIN_SCORE = _d.AI_MIN_SCORE
    AI_DOC_RETRIEVAL_TOP_K = _d.AI_DOC_RETRIEVAL_TOP_K

    # Clone + analysis limits
    API_MAX_REPO_SIZE_MB = _d.API_MAX_REPO_SIZE_MB
    API_MAX_REPO_FILES = _d.API_MAX_REPO_FILES
    API_MAX_FILE_BYTES = _d.API_MAX_FILE_BYTES
    CLONE_DEPTH = _d.CLONE_DEPTH
    CLONE_TIMEOUT_SECONDS = _d.CLONE_TIMEOUT_SECONDS
    ENGINE_PARSE_WORKERS = _d.ENGINE_PARSE_WORKERS
except ImportError:  # pragma: no cover - standalone engine fallback
    # Ollama (local provider)
    OLLAMA_BASE_URL = "http://localhost:11434"
    OLLAMA_CHAT_MODEL = "deepseek-coder:6.7b"
    OLLAMA_EMBED_MODEL = "nomic-embed-text"
    OLLAMA_TIMEOUT_SECONDS = 120
    OLLAMA_MAX_RETRIES = 3

    # Groq (cloud LLM)
    GROQ_BASE_URL = "https://api.groq.com/openai/v1"
    GROQ_CHAT_MODEL = "llama-3.3-70b-versatile"
    GROQ_TIMEOUT_SECONDS = 120
    GROQ_MAX_RETRIES = 3

    # HuggingFace (cloud embeddings)
    HUGGINGFACE_BASE_URL = "https://router.huggingface.co"
    HUGGINGFACE_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
    HUGGINGFACE_TIMEOUT_SECONDS = 60
    HUGGINGFACE_MAX_RETRIES = 3

    # Local embeddings
    LOCAL_EMBED_MODEL = "all-MiniLM-L6-v2"

    # ChromaDB
    CHROMA_HOST = "localhost"
    CHROMA_PORT = 8000
    CHROMA_COLLECTION_PREFIX = "repo_"
    CHROMA_DISTANCE = "cosine"

    # RAG / embedding
    AI_EMBEDDING_BATCH_SIZE = 16
    AI_TOP_K_CHUNKS = 8
    AI_TEMPERATURE = 0.2
    AI_MIN_SCORE = 0.0
    AI_DOC_RETRIEVAL_TOP_K = 12

    # Clone + analysis limits
    API_MAX_REPO_SIZE_MB = 500
    API_MAX_REPO_FILES = 5000
    API_MAX_FILE_BYTES = 2 * 1024 * 1024
    CLONE_DEPTH = 1
    CLONE_TIMEOUT_SECONDS = 300
    ENGINE_PARSE_WORKERS = 4
