"""Domain + HTTP exception hierarchy.

Domain exceptions are raised by services and translated to HTTP responses by
the FastAPI exception handlers registered in `app.main`.
"""
from __future__ import annotations

from typing import Any


class DomainError(Exception):
    """Base class for all domain-layer errors. Never raised raw to the client."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
class InvalidRepositoryURLError(DomainError):
    status_code = 400
    error_code = "invalid_repository_url"


class PathTraversalError(DomainError):
    status_code = 400
    error_code = "path_traversal_detected"


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------
class NotFoundError(DomainError):
    status_code = 404
    error_code = "not_found"


class RepositoryNotFoundError(NotFoundError):
    error_code = "repository_not_found"


class AnalysisJobNotFoundError(NotFoundError):
    error_code = "analysis_job_not_found"


class SourceFileNotFoundError(NotFoundError):
    error_code = "source_file_not_found"


class UserNotFoundError(NotFoundError):
    error_code = "user_not_found"


# ---------------------------------------------------------------------------
# Authentication / authorization
# ---------------------------------------------------------------------------
class UnauthorizedError(DomainError):
    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(DomainError):
    status_code = 403
    error_code = "forbidden"


# ---------------------------------------------------------------------------
# Conflict / state
# ---------------------------------------------------------------------------
class ConflictError(DomainError):
    status_code = 409
    error_code = "conflict"


class RepositoryAlreadyExistsError(ConflictError):
    error_code = "repository_already_exists"


class AnalysisAlreadyRunningError(ConflictError):
    error_code = "analysis_already_running"


class AnalysisNotReadyError(ConflictError):
    status_code = 409
    error_code = "analysis_not_ready"


# ---------------------------------------------------------------------------
# External dependencies
# ---------------------------------------------------------------------------
class ExternalServiceError(DomainError):
    status_code = 502
    error_code = "external_service_error"


class OllamaUnavailableError(ExternalServiceError):
    error_code = "ollama_unavailable"


class ChromaUnavailableError(ExternalServiceError):
    error_code = "chroma_unavailable"


class QueueUnavailableError(ExternalServiceError):
    error_code = "queue_unavailable"


# ---------------------------------------------------------------------------
# Rate limiting / quotas
# ---------------------------------------------------------------------------
class RateLimitExceededError(DomainError):
    status_code = 429
    error_code = "rate_limit_exceeded"


class QuotaExceededError(DomainError):
    status_code = 413
    error_code = "quota_exceeded"
