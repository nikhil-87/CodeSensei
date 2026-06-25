"""Star DTOs — toggle responses for the GitHub-style star feature."""
from __future__ import annotations

from pydantic import BaseModel, Field


class StarState(BaseModel):
    """The viewer's star relationship with a repository after a toggle."""

    starred: bool = Field(description="Whether the current user now stars this repo.")
    star_count: int = Field(
        ge=0, description="Total number of stars on the repository."
    )
