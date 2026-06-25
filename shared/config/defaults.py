"""Centralized default configuration values.

All default values used across the application are defined here. Services
should import these defaults rather than hardcoding values. This enables:

1. Single source of truth for configuration defaults
2. Easy auditing of all configurable values
3. Consistent defaults across services (backend, worker, analysis-engine)
4. Simple updates when defaults need to change

Example:
    from shared.config.defaults import POSTGRES_HOST, POSTGRES_PORT

    class Settings(BaseSettings):
        postgres_host: str = Field(default=POSTGRES_HOST)
        postgres_port: int = Field(default=POSTGRES_PORT)
"""
from __future__ import annotations

# =============================================================================
# Application
# =============================================================================
APP_NAME = "codesensei"
APP_ENV = "development"
APP_LOG_LEVEL = "INFO"
APP_DEBUG = False
APP_SECRET_KEY = "dev-secret-change-me-min-32-characters-long"  # Override in production!

# CORS - comma-separated origins for development
CORS_ORIGINS_DEV = "http://localhost:5173,http://localhost:3000"

# =============================================================================
# Authentication (GitHub OAuth + cookie sessions)
# =============================================================================
# Register a GitHub OAuth App and set these via environment / .env in production.
GITHUB_OAUTH_CLIENT_ID = ""
GITHUB_OAUTH_CLIENT_SECRET = ""  # Override in production!
# Where GitHub redirects after authorization. Must match the OAuth App setting.
GITHUB_OAUTH_CALLBACK_URL = "http://localhost:3000/api/v1/auth/github/callback"
# Where the backend redirects the browser after a successful login.
FRONTEND_BASE_URL = "http://localhost:3000"
# Session cookie holding the signed JWT.
SESSION_COOKIE_NAME = "codesensei_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
# Dev-only password-less login (disabled automatically outside development/test).
AUTH_DEV_LOGIN_ENABLED = True

# =============================================================================
# Mock Authentication (local development & automated tests ONLY)
# =============================================================================
# When MOCK_AUTH=true the app skips GitHub OAuth and treats every request as a
# single predefined mock user. This is HARD-DISABLED whenever APP_ENV=production
# (see Settings.mock_auth_enabled) so it can never be turned on by accident in a
# production deployment. Use it for offline dev and for running the test suite
# without real OAuth credentials.
MOCK_AUTH = False
MOCK_AUTH_GITHUB_ID = 424242  # stable, clearly-fake id reserved for the mock user
MOCK_AUTH_USERNAME = "mockuser"
MOCK_AUTH_DISPLAY_NAME = "Mock User"
MOCK_AUTH_EMAIL = "mockuser@example.com"
MOCK_AUTH_AVATAR_URL = "https://avatars.githubusercontent.com/u/0"

# =============================================================================
# Feature Flags
# =============================================================================
# Toggle non-critical functionality without code changes. Driven by env vars
# (FEATURE_*). Keep defaults conservative; enable per-environment as needed.
FEATURE_AI_CHAT_ENABLED = True
FEATURE_ANALYTICS_ENABLED = False
FEATURE_NOTIFICATIONS_ENABLED = False

# =============================================================================
# API Server
# =============================================================================
API_HOST = "0.0.0.0"
API_PORT = 8000
API_WORKERS = 4
API_REQUEST_TIMEOUT_SECONDS = 120
API_MAX_REPO_SIZE_MB = 500
API_MAX_REPO_FILES = 5000
API_MAX_FILE_BYTES = 2 * 1024 * 1024  # 2 MB — skip files larger than this
API_RATE_LIMIT_PER_MINUTE = 60

# =============================================================================
# Analysis Engine (clone + parse tuning)
# =============================================================================
CLONE_DEPTH = 1
CLONE_TIMEOUT_SECONDS = 300
ENGINE_PARSE_WORKERS = 4

# =============================================================================
# PostgreSQL
# =============================================================================
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_DB = "codesensei"
POSTGRES_USER = "codesensei"
POSTGRES_PASSWORD = "codesensei"  # Override in production!
POSTGRES_SSLMODE = ""  # Set to "require" for Neon/cloud Postgres
POSTGRES_POOL_SIZE = 10
POSTGRES_POOL_SIZE_WORKER = 5  # Workers use smaller pool
POSTGRES_MAX_OVERFLOW = 20

# =============================================================================
# Redis
# =============================================================================
REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = ""  # Override in production!
REDIS_TLS = False  # Set to True for Upstash/cloud Redis
REDIS_QUEUE_NAME = "analysis-jobs"
REDIS_CACHE_TTL_SECONDS = 3600  # 1 hour
REDIS_SOCKET_TIMEOUT_SECONDS = 10
REDIS_SOCKET_CONNECT_TIMEOUT_SECONDS = 10
REDIS_SOCKET_TIMEOUT_DISPATCHER = 5  # Shorter timeout for API dispatching
# TCP keepalive tuning (required for serverless Redis like Upstash)
REDIS_KEEPALIVE_IDLE_SECONDS = 5
REDIS_KEEPALIVE_INTERVAL_SECONDS = 2
REDIS_KEEPALIVE_COUNT = 3

# =============================================================================
# ChromaDB (Vector Store)
# =============================================================================
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000  # ChromaDB always binds 8000 internally
CHROMA_COLLECTION_PREFIX = "repo_"
CHROMA_DISTANCE = "cosine"

# =============================================================================
# Worker
# =============================================================================
WORKER_CONCURRENCY = 2
WORKER_JOB_TIMEOUT_SECONDS = 1800  # 30 minutes
WORKER_RETRY_MAX_ATTEMPTS = 3
WORKER_CLONE_DIR = "/var/lib/codesensei/workspaces"
WORKER_PROGRESS_THROTTLE_FILES = 25
WORKER_INDEXING_ENABLED = True
WORKER_RQ_RESULT_TTL_SECONDS = 86400  # 1 day
WORKER_POLL_INTERVAL_SECONDS = 5  # Must stay < 15s for Upstash idle timeout

# =============================================================================
# Stuck-job reaper (backend background task)
# =============================================================================
# A RUNNING job whose worker crashed would otherwise stay RUNNING forever and,
# via the active-job unique index, permanently block re-analysis of that repo.
# The reaper marks such jobs FAILED so the repository unblocks automatically.
ANALYSIS_REAPER_ENABLED = True
ANALYSIS_REAPER_INTERVAL_SECONDS = 60  # how often the sweep runs
# RUNNING is considered dead when no heartbeat for this long. Must exceed the
# longest gap between worker heartbeats (a slow clone/embed of a large repo).
ANALYSIS_RUNNING_HEARTBEAT_TIMEOUT_SECONDS = 900  # 15 minutes
# QUEUED that never gets picked up (worker down / lost RQ job) is failed after
# this long so the user isn't stuck waiting on a job that will never run.
ANALYSIS_QUEUED_TIMEOUT_SECONDS = 1800  # 30 minutes

# =============================================================================
# AI / LLM Settings
# =============================================================================
AI_MAX_CONTEXT_TOKENS = 8192
AI_TOP_K_CHUNKS = 8
AI_EMBEDDING_BATCH_SIZE = 16
AI_TEMPERATURE = 0.2
AI_MIN_SCORE = 0.0
AI_DOC_RETRIEVAL_TOP_K = 12

# =============================================================================
# Ollama (Local LLM)
# =============================================================================
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_CHAT_MODEL = "deepseek-coder:6.7b"
OLLAMA_EMBED_MODEL = "nomic-embed-text"
OLLAMA_TIMEOUT_SECONDS = 120
OLLAMA_MAX_RETRIES = 3

# =============================================================================
# Groq (Free Cloud LLM)
# =============================================================================
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CHAT_MODEL = "llama-3.3-70b-versatile"
GROQ_MAX_RETRIES = 3
GROQ_TIMEOUT_SECONDS = 120

# =============================================================================
# HuggingFace (Free Cloud Embeddings)
# =============================================================================
HUGGINGFACE_BASE_URL = "https://router.huggingface.co"
HUGGINGFACE_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
HUGGINGFACE_MAX_RETRIES = 3
HUGGINGFACE_TIMEOUT_SECONDS = 60

# =============================================================================
# Local Embeddings (CPU-friendly)
# =============================================================================
LOCAL_EMBED_MODEL = "all-MiniLM-L6-v2"

# =============================================================================
# Observability
# =============================================================================
METRICS_ENABLED = True
METRICS_PORT_BACKEND = 9100
METRICS_PORT_WORKER = 9101
TRACING_ENABLED = False
OTEL_EXPORTER_OTLP_ENDPOINT = ""

# =============================================================================
# Frontend
# =============================================================================
FRONTEND_API_TIMEOUT_MS = 30000  # 30 seconds
FRONTEND_DEV_PORT = 5173
FRONTEND_PROD_PORT = 3000

# =============================================================================
# HTTP Client Settings
# =============================================================================
HTTP_RETRY_ATTEMPTS = 3
HTTP_RETRY_WAIT_MIN_SECONDS = 1
HTTP_RETRY_WAIT_MAX_SECONDS = 10
HTTP_RETRY_MULTIPLIER = 2
