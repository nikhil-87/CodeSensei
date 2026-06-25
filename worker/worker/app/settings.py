"""Worker settings — env-driven, mirrors the backend's relevant config.

Uses shared configuration defaults from shared.config.defaults for consistency
across all services. All configurable values can be overridden via environment
variables or .env file.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import shared defaults - use try/except for standalone testing
try:
    from shared.config import defaults
except ImportError:
    # Fallback for standalone worker testing without shared module
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from shared.config import defaults

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LLMProvider = Literal["ollama", "groq"]
EmbeddingProvider = Literal["ollama", "huggingface", "local"]


class WorkerSettings(BaseSettings):
    """Worker-side configuration.

    The worker reads the *same* env file as the backend so a single .env
    drives the whole stack. Variable names are kept identical where they
    overlap.
    
    All defaults are sourced from shared.config.defaults for consistency.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Postgres (sync driver) ------------------------------------------
    postgres_host: str = Field(default=defaults.POSTGRES_HOST)
    postgres_port: int = Field(default=defaults.POSTGRES_PORT)
    postgres_db: str = Field(default=defaults.POSTGRES_DB)
    postgres_user: str = Field(default=defaults.POSTGRES_USER)
    postgres_password: str = Field(default=defaults.POSTGRES_PASSWORD)
    postgres_sslmode: str = Field(default=defaults.POSTGRES_SSLMODE)
    postgres_pool_size: int = Field(default=defaults.POSTGRES_POOL_SIZE_WORKER)

    # ----- Redis ------------------------------------------------------------
    redis_host: str = Field(default=defaults.REDIS_HOST)
    redis_port: int = Field(default=defaults.REDIS_PORT)
    redis_db: int = Field(default=defaults.REDIS_DB)
    redis_password: str = Field(default=defaults.REDIS_PASSWORD)
    redis_tls: bool = Field(default=defaults.REDIS_TLS)
    redis_queue_name: str = Field(default=defaults.REDIS_QUEUE_NAME)
    redis_socket_timeout: int = Field(default=defaults.REDIS_SOCKET_TIMEOUT_SECONDS)
    redis_socket_connect_timeout: int = Field(default=defaults.REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS)
    redis_keepalive_idle: int = Field(default=defaults.REDIS_KEEPALIVE_IDLE_SECONDS)
    redis_keepalive_interval: int = Field(default=defaults.REDIS_KEEPALIVE_INTERVAL_SECONDS)
    redis_keepalive_count: int = Field(default=defaults.REDIS_KEEPALIVE_COUNT)

    # ----- ChromaDB ---------------------------------------------------------
    chroma_host: str = Field(default=defaults.CHROMA_HOST)
    chroma_port: int = Field(default=defaults.CHROMA_PORT)
    chroma_collection_prefix: str = Field(default=defaults.CHROMA_COLLECTION_PREFIX)

    # ----- AI Provider Selection --------------------------------------------
    llm_provider: LLMProvider = Field(default="ollama")
    embedding_provider: EmbeddingProvider = Field(default="ollama")

    # ----- Ollama / AI (local provider) -------------------------------------
    ollama_base_url: str = Field(default=defaults.OLLAMA_BASE_URL)
    ollama_chat_model: str = Field(default=defaults.OLLAMA_CHAT_MODEL)
    ollama_embed_model: str = Field(default=defaults.OLLAMA_EMBED_MODEL)
    ollama_timeout_seconds: int = Field(default=defaults.OLLAMA_TIMEOUT_SECONDS)

    # ----- Groq (free cloud LLM) --------------------------------------------
    groq_api_key: str = Field(default="")
    groq_chat_model: str = Field(default=defaults.GROQ_CHAT_MODEL)

    # ----- HuggingFace (free cloud embeddings) ------------------------------
    huggingface_api_key: str = Field(default="")
    huggingface_embed_model: str = Field(default=defaults.HUGGINGFACE_EMBED_MODEL)

    # ----- Local embeddings (CPU-friendly) ----------------------------------
    local_embed_model: str = Field(default=defaults.LOCAL_EMBED_MODEL)

    # ----- Worker -----------------------------------------------------------
    worker_concurrency: int = Field(default=defaults.WORKER_CONCURRENCY)
    worker_job_timeout_seconds: int = Field(default=defaults.WORKER_JOB_TIMEOUT_SECONDS)
    worker_clone_dir: str = Field(default=defaults.WORKER_CLONE_DIR)
    api_max_repo_size_mb: int = Field(default=defaults.API_MAX_REPO_SIZE_MB)
    api_max_repo_files: int = Field(default=defaults.API_MAX_REPO_FILES)
    worker_progress_throttle_files: int = Field(default=defaults.WORKER_PROGRESS_THROTTLE_FILES)
    worker_indexing_enabled: bool = Field(default=defaults.WORKER_INDEXING_ENABLED)
    worker_rq_result_ttl: int = Field(default=defaults.WORKER_RQ_RESULT_TTL_SECONDS)
    worker_poll_interval_seconds: int = Field(default=defaults.WORKER_POLL_INTERVAL_SECONDS)

    # ----- Observability ----------------------------------------------------
    app_log_level: LogLevel = Field(default=defaults.APP_LOG_LEVEL)
    metrics_enabled: bool = Field(default=defaults.METRICS_ENABLED)
    metrics_port: int = Field(default=defaults.METRICS_PORT_WORKER)

    # ------------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------------
    @property
    def postgres_dsn_sync(self) -> str:
        base = (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        if self.postgres_sslmode:
            return f"{base}?sslmode={self.postgres_sslmode}"
        return base

    @property
    def redis_url(self) -> str:
        scheme = "rediss" if self.redis_tls else "redis"
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"{scheme}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def workspace_root(self) -> Path:
        return Path(self.worker_clone_dir)

    @property
    def active_embed_model(self) -> str:
        """The embedding model name for the currently-selected provider."""
        return {
            "ollama": self.ollama_embed_model,
            "huggingface": self.huggingface_embed_model,
            "local": self.local_embed_model,
        }.get(self.embedding_provider, self.embedding_provider)

    @property
    def embedding_signature(self) -> str:
        """``provider:model`` identifier stamped onto each AI index build."""
        from shared.config.analysis_version import embedding_signature

        return embedding_signature(self.embedding_provider, self.active_embed_model)


@lru_cache(maxsize=1)
def get_settings() -> WorkerSettings:
    return WorkerSettings()
