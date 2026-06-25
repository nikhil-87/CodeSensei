"""Public profile DTOs — the read-only ``/u/{username}`` view."""
from __future__ import annotations

from pydantic import BaseModel, Field


class PublicProfileRead(BaseModel):
    """A user's public-facing profile summary.

    Intentionally excludes private fields (e.g. email): this is served to
    anonymous visitors of ``/users/{username}``.
    """

    username: str
    display_name: str | None = None
    avatar_url: str | None = None
    public_repository_count: int = Field(
        ge=0, description="Number of the user's public, analyzed repositories."
    )
    total_stars: int = Field(
        ge=0, description="Total stars received across the user's public repos."
    )
