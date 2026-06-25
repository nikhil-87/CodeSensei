"""Application settings — Pydantic v2 + 12-factor env loading.

Uses shared configuration defaults from shared.config.defaults for consistency
across all services. All configurable values can be overridden via environment
variables or .env file.
"""
from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Import shared defaults - add parent to path if needed
try:
    from shared.config import defaults
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
    from shared.config import defaults

EnvName = Literal["development", "staging", "production", "test"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LLMProvider = Literal["ollama", "groq"]
EmbeddingProvider = Literal["ollama", "huggingface", "local"]


class Settings(BaseSettings):
    """All configuration in one place. Loaded from environment / .env file.

    Conventions:
        - Group prefixes mirror env var names (APP_*, API_*, POSTGRES_*, ...).
        - Defaults are dev-friendly; prod overrides come from .env or the orchestrator.
        - No secret has a default that would be safe in production.
        - All defaults are sourced from shared.config.defaults for consistency.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # ----- Application ------------------------------------------------------
    app_name: str = Field(default=defaults.APP_NAME)
    app_env: EnvName = Field(default=defaults.APP_ENV)
    app_log_level: LogLevel = Field(default=defaults.APP_LOG_LEVEL)
    app_debug: bool = Field(default=defaults.APP_DEBUG)
    app_secret_key: str = Field(default=defaults.APP_SECRET_KEY)
    app_cors_origins: str = Field(default=defaults.CORS_ORIGINS_DEV)

    # ----- Authentication (GitHub OAuth + cookie sessions) ------------------
    github_oauth_client_id: str = Field(default=defaults.GITHUB_OAUTH_CLIENT_ID)
    github_oauth_client_secret: str = Field(default=defaults.GITHUB_OAUTH_CLIENT_SECRET)
    github_oauth_callback_url: str = Field(default=defaults.GITHUB_OAUTH_CALLBACK_URL)
    frontend_base_url: str = Field(default=defaults.FRONTEND_BASE_URL)
    session_cookie_name: str = Field(default=defaults.SESSION_COOKIE_NAME)
    session_ttl_seconds: int = Field(default=defaults.SESSION_TTL_SECONDS)
    auth_dev_login_enabled: bool = Field(default=defaults.AUTH_DEV_LOGIN_ENABLED)

    # ----- Mock Authentication (local dev / tests only) ---------------------
    # HARD-DISABLED in production via the `mock_auth_enabled` property below.
    mock_auth: bool = Field(default=defaults.MOCK_AUTH)
    mock_auth_github_id: int = Field(default=defaults.MOCK_AUTH_GITHUB_ID)
    mock_auth_username: str = Field(default=defaults.MOCK_AUTH_USERNAME)
    mock_auth_display_name: str = Field(default=defaults.MOCK_AUTH_DISPLAY_NAME)
    mock_auth_email: str = Field(default=defaults.MOCK_AUTH_EMAIL)
    mock_auth_avatar_url: str = Field(default=defaults.MOCK_AUTH_AVATAR_URL)

    # ----- Feature flags ----------------------------------------------------
    feature_ai_chat_enabled: bool = Field(default=defaults.FEATURE_AI_CHAT_ENABLED)
    feature_analytics_enabled: bool = Field(default=defaults.FEATURE_ANALYTICS_ENABLED)
    feature_notifications_enabled: bool = Field(
        default=defaults.FEATURE_NOTIFICATIONS_ENABLED
    )

    # ----- API --------------------------------------------------------------
    api_host: str = Field(default=defaults.API_HOST)
    api_port: int = Field(default=defaults.API_PORT)
    api_workers: int = Field(default=defaults.API_WORKERS)
    api_request_timeout_seconds: int = Field(default=defaults.API_REQUEST_TIMEOUT_SECONDS)
    api_max_repo_size_mb: int = Field(default=defaults.API_MAX_REPO_SIZE_MB)
    api_max_repo_files: int = Field(default=defaults.API_MAX_REPO_FILES)
    api_rate_limit_per_minute: int = Field(default=defaults.API_RATE_LIMIT_PER_MINUTE)

    # ----- Postgres ---------------------------------------------------------
    postgres_host: str = Field(default=defaults.POSTGRES_HOST)
    postgres_port: int = Field(default=defaults.POSTGRES_PORT)
    postgres_db: str = Field(default=defaults.POSTGRES_DB)
    postgres_user: str = Field(default=defaults.POSTGRES_USER)
    postgres_password: str = Field(default=defaults.POSTGRES_PASSWORD)
    postgres_sslmode: str = Field(default=defaults.POSTGRES_SSLMODE)
    postgres_pool_size: int = Field(default=defaults.POSTGRES_POOL_SIZE)
    postgres_max_overflow: int = Field(default=defaults.POSTGRES_MAX_OVERFLOW)

    # ----- Redis ------------------------------------------------------------
    redis_host: str = Field(default=defaults.REDIS_HOST)
    redis_port: int = Field(default=defaults.REDIS_PORT)
    redis_db: int = Field(default=defaults.REDIS_DB)
    redis_password: str = Field(default=defaults.REDIS_PASSWORD)
    redis_tls: bool = Field(default=defaults.REDIS_TLS)
    redis_queue_name: str = Field(default=defaults.REDIS_QUEUE_NAME)
    redis_cache_ttl_seconds: int = Field(default=defaults.REDIS_CACHE_TTL_SECONDS)
    redis_socket_timeout: int = Field(default=defaults.REDIS_SOCKET_TIMEOUT_DISPATCHER)
    redis_socket_connect_timeout: int = Field(default=defaults.REDIS_SOCKET_TIMEOUT_DISPATCHER)

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

    # ----- AI general settings ----------------------------------------------
    ai_max_context_tokens: int = Field(default=defaults.AI_MAX_CONTEXT_TOKENS)
    ai_top_k_chunks: int = Field(default=defaults.AI_TOP_K_CHUNKS)

    # ----- Worker -----------------------------------------------------------
    worker_concurrency: int = Field(default=defaults.WORKER_CONCURRENCY)
    worker_job_timeout_seconds: int = Field(default=defaults.WORKER_JOB_TIMEOUT_SECONDS)
    worker_retry_max_attempts: int = Field(default=defaults.WORKER_RETRY_MAX_ATTEMPTS)
    worker_clone_dir: str = Field(default=defaults.WORKER_CLONE_DIR)

    # ----- Stuck-job reaper -------------------------------------------------
    analysis_reaper_enabled: bool = Field(default=defaults.ANALYSIS_REAPER_ENABLED)
    analysis_reaper_interval_seconds: int = Field(
        default=defaults.ANALYSIS_REAPER_INTERVAL_SECONDS
    )
    analysis_running_heartbeat_timeout_seconds: int = Field(
        default=defaults.ANALYSIS_RUNNING_HEARTBEAT_TIMEOUT_SECONDS
    )
    analysis_queued_timeout_seconds: int = Field(
        default=defaults.ANALYSIS_QUEUED_TIMEOUT_SECONDS
    )

    # ----- Observability ----------------------------------------------------
    metrics_enabled: bool = Field(default=defaults.METRICS_ENABLED)
    metrics_port: int = Field(default=defaults.METRICS_PORT_BACKEND)
    tracing_enabled: bool = Field(default=defaults.TRACING_ENABLED)
    otel_exporter_otlp_endpoint: str = Field(default=defaults.OTEL_EXPORTER_OTLP_ENDPOINT)

    # ------------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------------
    @field_validator("app_secret_key")
    @classmethod
    def _validate_secret(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("APP_SECRET_KEY must be at least 32 characters long")
        return v

    @model_validator(mode="after")
    def _harden_production(self) -> "Settings":
        """Refuse to start in production with known-insecure defaults.

        The repository ships dev-friendly defaults (a public secret key, a
        default Postgres password) so the app runs out of the box locally.
        Those exact values are committed to source control, so anyone could
        forge session JWTs or reach the database if they leaked into a real
        deployment. Fail fast and loudly instead of silently trusting them.
        """
        if self.app_env != "production":
            return self

        problems: list[str] = []
        if self.app_secret_key == defaults.APP_SECRET_KEY:
            problems.append(
                "APP_SECRET_KEY is still the public development default — set a "
                "unique secret (e.g. `openssl rand -hex 32`)."
            )
        if self.postgres_password == defaults.POSTGRES_PASSWORD:
            problems.append(
                "POSTGRES_PASSWORD is still the development default — set a strong "
                "database password."
            )
        if self.app_debug:
            problems.append("APP_DEBUG must be false in production.")
        if not self.github_oauth_enabled and not self.mock_auth:
            # Not strictly fatal, but a production app with no login configured
            # is almost certainly a misconfiguration.
            problems.append(
                "No authentication is configured (GitHub OAuth credentials are "
                "empty). Configure GITHUB_OAUTH_CLIENT_ID/SECRET."
            )
        if problems:
            raise ValueError(
                "Insecure production configuration: " + " ".join(problems)
            )
        return self


    # ------------------------------------------------------------------------
    # Derived properties
    # ------------------------------------------------------------------------
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"

    @property
    def github_oauth_enabled(self) -> bool:
        """True when GitHub OAuth credentials are configured."""
        return bool(self.github_oauth_client_id and self.github_oauth_client_secret)

    @property
    def dev_login_enabled(self) -> bool:
        """Dev-only password-less login — never available in production."""
        return self.auth_dev_login_enabled and self.app_env in ("development", "test")

    @property
    def mock_auth_enabled(self) -> bool:
        """Mock authentication, hard-disabled in production.

        Safeguard: even if ``MOCK_AUTH=true`` is set in a production environment
        (by mistake or a leaked .env), this returns ``False`` so no request is
        ever auto-authenticated in production. ``main.py`` logs a loud error when
        the flag is set but ignored.
        """
        return self.mock_auth and self.app_env != "production"

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.app_cors_origins.split(",") if o.strip()]

    @property
    def postgres_dsn_async(self) -> str:
        base = (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
        if self.postgres_sslmode:
            return f"{base}?ssl={self.postgres_sslmode}"
        return base

    @property
    def redis_url(self) -> str:
        scheme = "rediss" if self.redis_tls else "redis"
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"{scheme}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def chroma_url(self) -> str:
        return f"http://{self.chroma_host}:{self.chroma_port}"

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
        """``provider:model`` identifier for the configured embedding strategy.

        Compared against an analysis's stored ``embedding_model`` to detect an
        AI vector index built with a now-different model.
        """
        from shared.config.analysis_version import embedding_signature

        return embedding_signature(self.embedding_provider, self.active_embed_model)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings accessor. Tests can override via dependency_overrides."""
    return Settings()
