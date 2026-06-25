"""Repository DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from app.models.repository import RepositoryStatus
from app.schemas.common import ORMBase

# Sort order for public discovery + profile repository listings.
RepositorySort = Literal["stars", "recent", "name"]


class RepositoryCreate(BaseModel):
    url: HttpUrl = Field(
        description="HTTPS URL of a public GitHub repository.",
        examples=["https://github.com/psf/requests"],
    )
    branch: str | None = Field(
        default=None,
        max_length=255,
        description="Optional branch name. Defaults to the repository's default branch.",
    )


class RepositoryFreshness(BaseModel):
    """Whether a stored analysis was produced by the current pipeline."""

    state: str = Field(
        description="fresh | stale | unknown | unavailable",
        examples=["fresh"],
    )
    reasons: list[str] = Field(
        default_factory=list,
        description="Human-readable explanations of why a refresh is suggested.",
    )
    affected_features: list[str] = Field(
        default_factory=list,
        description="Product features impacted by an out-of-date analysis.",
    )
    can_refresh: bool = Field(
        default=False,
        description="True when re-running analysis would resolve the issue.",
    )


class RepositoryRead(ORMBase):
    id: uuid.UUID
    url: str
    branch: str | None
    default_branch: str | None
    name: str
    owner: str
    owner_id: uuid.UUID | None
    is_public: bool
    status: RepositoryStatus
    error_message: str | None
    analyzed_at: datetime | None
    file_count: int
    total_lines: int
    languages: str | None
    # Social: denormalized star count (public) + whether the *current viewer*
    # has starred this repo (populated per-request by the endpoint layer).
    star_count: int = 0
    viewer_has_starred: bool = False
    # Provenance + versioning of the last successful analysis.
    commit_hash: str | None = None
    analysis_version: int | None = None
    pipeline_version: int | None = None
    schema_version: int | None = None
    embedding_model: str | None = None
    # Computed freshness verdict (populated by the service layer, not the ORM).
    freshness: RepositoryFreshness | None = None
    created_at: datetime
    updated_at: datetime


class RepositoryStats(BaseModel):
    file_count: int
    total_lines: int
    languages: dict[str, int]  # language → file count
    function_count: int
    class_count: int
    avg_cyclomatic: float
    max_cyclomatic: int
    circular_dependency_count: int
    dead_code_file_count: int


class RepositoryDetail(RepositoryRead):
    stats: RepositoryStats | None = None
