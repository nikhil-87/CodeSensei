"""Test configuration utilities.

Provides factory functions and fixtures for creating test configurations
that use sensible defaults while allowing easy overrides. This ensures
tests are isolated from environment variables while still being able to
test configuration-dependent behavior.

Usage:
    from shared.config.testing import make_test_settings
    
    settings = make_test_settings(postgres_db="test_db")
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from shared.config import defaults


def make_test_worker_settings(tmp_path: Path | None = None, **overrides: Any) -> dict[str, Any]:
    """Create worker settings dict for tests with sensible test defaults.
    
    Args:
        tmp_path: Temporary directory for workspace (pytest fixture)
        **overrides: Any settings to override
    
    Returns:
        Dictionary suitable for WorkerSettings(**result)
    """
    workspace_dir = str(tmp_path / "workspace") if tmp_path else "/tmp/test-workspace"
    
    base = {
        # Postgres - use test database
        "postgres_host": defaults.POSTGRES_HOST,
        "postgres_port": defaults.POSTGRES_PORT,
        "postgres_user": defaults.POSTGRES_USER,
        "postgres_password": defaults.POSTGRES_PASSWORD,
        "postgres_db": "codesensei_test",
        "postgres_pool_size": 2,  # Smaller pool for tests
        
        # Redis
        "redis_host": defaults.REDIS_HOST,
        "redis_port": defaults.REDIS_PORT,
        "redis_db": 15,  # Use different DB for tests
        "redis_password": defaults.REDIS_PASSWORD,
        "redis_queue_name": "test-analysis-jobs",
        "redis_socket_timeout": 5,
        "redis_socket_connect_timeout": 5,
        
        # ChromaDB
        "chroma_host": defaults.CHROMA_HOST,
        "chroma_port": defaults.CHROMA_PORT,
        "chroma_collection_prefix": "test_repo_",
        
        # AI - use minimal timeouts for tests
        "llm_provider": "ollama",
        "embedding_provider": "ollama",
        "ollama_base_url": defaults.OLLAMA_BASE_URL,
        "ollama_chat_model": "test-model",
        "ollama_embed_model": "test-embed",
        "ollama_timeout_seconds": 10,
        "groq_api_key": "",
        "groq_chat_model": defaults.GROQ_CHAT_MODEL,
        "huggingface_api_key": "",
        "huggingface_embed_model": defaults.HUGGINGFACE_EMBED_MODEL,
        "local_embed_model": defaults.LOCAL_EMBED_MODEL,
        
        # Worker - smaller limits for tests
        "worker_concurrency": 1,
        "worker_job_timeout_seconds": 60,
        "worker_clone_dir": workspace_dir,
        "api_max_repo_size_mb": 50,
        "api_max_repo_files": 100,
        "worker_progress_throttle_files": 5,
        "worker_indexing_enabled": True,
        "worker_rq_result_ttl": 60,
        
        # Observability
        "app_log_level": "WARNING",
        "metrics_enabled": False,
        "metrics_port": defaults.METRICS_PORT_WORKER,
    }
    
    # Apply overrides
    base.update(overrides)
    return base


def make_test_backend_settings(tmp_path: Path | None = None, **overrides: Any) -> dict[str, Any]:
    """Create backend settings dict for tests with sensible test defaults.
    
    Args:
        tmp_path: Temporary directory (pytest fixture)
        **overrides: Any settings to override
    
    Returns:
        Dictionary suitable for Settings(**result)
    """
    workspace_dir = str(tmp_path / "workspace") if tmp_path else "/tmp/test-workspace"
    
    base = {
        # Application
        "app_name": defaults.APP_NAME,
        "app_env": "test",
        "app_log_level": "WARNING",
        "app_debug": False,
        "app_secret_key": "test-secret-key-minimum-32-characters-long",
        "app_cors_origins": "http://localhost:5173",
        
        # API
        "api_host": defaults.API_HOST,
        "api_port": defaults.API_PORT,
        "api_workers": 1,
        "api_request_timeout_seconds": 30,
        "api_max_repo_size_mb": 50,
        "api_max_repo_files": 100,
        "api_rate_limit_per_minute": 100,
        
        # Postgres
        "postgres_host": defaults.POSTGRES_HOST,
        "postgres_port": defaults.POSTGRES_PORT,
        "postgres_db": "codesensei_test",
        "postgres_user": defaults.POSTGRES_USER,
        "postgres_password": defaults.POSTGRES_PASSWORD,
        "postgres_pool_size": 2,
        "postgres_max_overflow": 5,
        
        # Redis
        "redis_host": defaults.REDIS_HOST,
        "redis_port": defaults.REDIS_PORT,
        "redis_db": 15,
        "redis_password": defaults.REDIS_PASSWORD,
        "redis_queue_name": "test-analysis-jobs",
        "redis_cache_ttl_seconds": 60,
        "redis_socket_timeout": 5,
        "redis_socket_connect_timeout": 5,
        
        # ChromaDB
        "chroma_host": defaults.CHROMA_HOST,
        "chroma_port": defaults.CHROMA_PORT,
        "chroma_collection_prefix": "test_repo_",
        
        # AI
        "llm_provider": "ollama",
        "embedding_provider": "ollama",
        "ollama_base_url": defaults.OLLAMA_BASE_URL,
        "ollama_chat_model": "test-model",
        "ollama_embed_model": "test-embed",
        "ollama_timeout_seconds": 10,
        "groq_api_key": "",
        "groq_chat_model": defaults.GROQ_CHAT_MODEL,
        "huggingface_api_key": "",
        "huggingface_embed_model": defaults.HUGGINGFACE_EMBED_MODEL,
        "local_embed_model": defaults.LOCAL_EMBED_MODEL,
        "ai_max_context_tokens": 2048,
        "ai_top_k_chunks": 4,
        
        # Worker
        "worker_concurrency": 1,
        "worker_job_timeout_seconds": 60,
        "worker_retry_max_attempts": 1,
        "worker_clone_dir": workspace_dir,
        
        # Observability
        "metrics_enabled": False,
        "metrics_port": defaults.METRICS_PORT_BACKEND,
        "tracing_enabled": False,
        "otel_exporter_otlp_endpoint": "",
    }
    
    # Apply overrides
    base.update(overrides)
    return base


def make_ai_runtime_config(repository_id: str = "test-repo", **overrides: Any) -> dict[str, Any]:
    """Create AIRuntimeConfig kwargs for tests.
    
    Args:
        repository_id: Repository ID for the runtime
        **overrides: Any settings to override
    
    Returns:
        Dictionary suitable for AIRuntimeConfig(**result)
    """
    base = {
        "repository_id": repository_id,
        "llm_provider": "ollama",
        "embedding_provider": "ollama",
        "ollama_base_url": defaults.OLLAMA_BASE_URL,
        "ollama_chat_model": "test-model",
        "ollama_embed_model": "test-embed",
        "ollama_timeout_seconds": 10.0,
        "groq_api_key": "",
        "groq_chat_model": defaults.GROQ_CHAT_MODEL,
        "huggingface_api_key": "",
        "huggingface_embed_model": defaults.HUGGINGFACE_EMBED_MODEL,
        "local_embed_model": defaults.LOCAL_EMBED_MODEL,
        "chroma_host": defaults.CHROMA_HOST,
        "chroma_port": defaults.CHROMA_PORT,
        "chroma_collection_prefix": "test_repo_",
        "chroma_distance": defaults.CHROMA_DISTANCE,
        "embedding_batch_size": 8,
    }
    
    base.update(overrides)
    return base
