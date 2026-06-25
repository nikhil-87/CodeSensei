"""AI Provider configuration and type definitions.

This module defines the supported AI providers and their configuration.
It provides a clean abstraction for switching between different LLM and
embedding providers without changing application code.

Supported Providers:
    LLM:
        - ollama: Local LLM via Ollama (requires 8GB+ RAM)
        - groq: Free cloud LLM API (rate limited)
    
    Embeddings:
        - ollama: Local embeddings via Ollama
        - huggingface: Free HuggingFace Inference API
        - local: CPU-friendly sentence-transformers (no API)

Example:
    from shared.config.providers import LLMProvider, EmbeddingProvider
    
    # Type-safe provider selection
    llm: LLMProvider = "groq"
    embeddings: EmbeddingProvider = "huggingface"
"""
from __future__ import annotations

from typing import Literal

# =============================================================================
# Provider Type Definitions
# =============================================================================

# LLM providers for chat/completion
LLMProvider = Literal["ollama", "groq"]

# Embedding providers for vector search
EmbeddingProvider = Literal["ollama", "huggingface", "local"]

# Environment names
EnvironmentName = Literal["development", "staging", "production", "test"]

# Log levels
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

# =============================================================================
# Default Provider Selection
# =============================================================================

# Default providers (Ollama for backward compatibility)
DEFAULT_LLM_PROVIDER: LLMProvider = "ollama"
DEFAULT_EMBEDDING_PROVIDER: EmbeddingProvider = "ollama"

# =============================================================================
# Provider Metadata
# =============================================================================

# Information about each provider for documentation/UI
LLM_PROVIDER_INFO = {
    "ollama": {
        "name": "Ollama (Local)",
        "description": "Run LLMs locally via Ollama",
        "requires_api_key": False,
        "requires_local_server": True,
        "min_ram_gb": 8,
        "free_tier": True,
        "rate_limited": False,
    },
    "groq": {
        "name": "Groq (Cloud)",
        "description": "Free cloud LLM API with fast inference",
        "requires_api_key": True,
        "requires_local_server": False,
        "min_ram_gb": 0,
        "free_tier": True,
        "rate_limited": True,
        "rate_limit": "30 requests/minute",
    },
}

EMBEDDING_PROVIDER_INFO = {
    "ollama": {
        "name": "Ollama (Local)",
        "description": "Local embeddings via Ollama",
        "requires_api_key": False,
        "requires_local_server": True,
        "free_tier": True,
        "rate_limited": False,
    },
    "huggingface": {
        "name": "HuggingFace (Cloud)",
        "description": "Free HuggingFace Inference API",
        "requires_api_key": True,
        "requires_local_server": False,
        "free_tier": True,
        "rate_limited": True,
    },
    "local": {
        "name": "Local (sentence-transformers)",
        "description": "CPU-friendly local embeddings, no API required",
        "requires_api_key": False,
        "requires_local_server": False,
        "free_tier": True,
        "rate_limited": False,
    },
}


def get_required_env_vars(llm_provider: LLMProvider, embedding_provider: EmbeddingProvider) -> list[str]:
    """Return list of required environment variables for the selected providers.
    
    Args:
        llm_provider: Selected LLM provider
        embedding_provider: Selected embedding provider
    
    Returns:
        List of required environment variable names
    """
    required = []
    
    if llm_provider == "groq":
        required.append("GROQ_API_KEY")
    
    if embedding_provider == "huggingface":
        required.append("HUGGINGFACE_API_KEY")
    
    return required


def validate_provider_config(
    llm_provider: LLMProvider,
    embedding_provider: EmbeddingProvider,
    groq_api_key: str = "",
    huggingface_api_key: str = "",
) -> list[str]:
    """Validate provider configuration and return list of errors.
    
    Args:
        llm_provider: Selected LLM provider
        embedding_provider: Selected embedding provider
        groq_api_key: Groq API key (if using Groq)
        huggingface_api_key: HuggingFace API key (if using HuggingFace)
    
    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    
    if llm_provider == "groq" and not groq_api_key:
        errors.append(
            "GROQ_API_KEY is required when LLM_PROVIDER='groq'. "
            "Get a free key at https://console.groq.com/keys"
        )
    
    if embedding_provider == "huggingface" and not huggingface_api_key:
        errors.append(
            "HUGGINGFACE_API_KEY is required when EMBEDDING_PROVIDER='huggingface'. "
            "Get a free token at https://huggingface.co/settings/tokens"
        )
    
    return errors
