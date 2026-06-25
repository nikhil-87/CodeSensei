"""Shared configuration module.

This module provides centralized default values and configuration constants
used across all services (backend, worker, analysis-engine). By defining
defaults in one place, we ensure consistency and make configuration changes
require updates in only one location.

Usage:
    from shared.config import defaults
    
    # Access default values
    host = os.getenv("POSTGRES_HOST", defaults.POSTGRES_HOST)
"""
from shared.config.defaults import *  # noqa: F401, F403
from shared.config.providers import *  # noqa: F401, F403
