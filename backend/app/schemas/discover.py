"""Discovery DTOs — repository-centric public browsing.

A single GitHub repository (``url`` + ``branch``) may be analyzed and made
public by several users. Discover lists the *repository* once (``DiscoverRepositoryRead``)
and a dedicated overview lists each public analysis (``PublicAnalysisRead``).
Only public-safe fields are ever exposed.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.repository import RepositoryFreshness


class DiscoverRepositoryRead(BaseModel):
    """One card in the repository-centric Discover grid."""

    url: str
    branch: str | None = None
    name: str
    owner: str
    analyses_count: int = Field(ge=0, description="Public analyses of this repository.")
    total_stars: int = Field(ge=0, description="Stars summed across public analyses.")
    latest_analyzed_at: datetime | None = None
    languages: str | None = None
    file_count: int = 0
    total_lines: int = 0
    # Representative (most-recent) analysis — lets the UI offer a 1-click open.
    latest_repository_id: uuid.UUID


class AnalystRef(BaseModel):
    """Public-safe reference to the user who produced an analysis."""

    username: str | None = None
    display_name: str | None = None
    avatar_url: str | None = None


class PublicAnalysisRead(BaseModel):
    """One public analysis of a repository (a single ``repositories`` row)."""

    repository_id: uuid.UUID
    analyst: AnalystRef
    analyzed_at: datetime | None = None
    star_count: int = 0
    viewer_has_starred: bool = False
    analysis_version: int | None = None
    pipeline_version: int | None = None
    schema_version: int | None = None
    file_count: int = 0
    total_lines: int = 0
    languages: str | None = None
    freshness: RepositoryFreshness | None = None


class RepositoryGroupDetail(BaseModel):
    """The repository overview page: header + every public analysis of it."""

    url: str
    branch: str | None = None
    name: str
    owner: str
    analyses_count: int = Field(ge=0)
    total_stars: int = Field(ge=0)
    latest_analyzed_at: datetime | None = None
    analyses: list[PublicAnalysisRead] = Field(default_factory=list)
