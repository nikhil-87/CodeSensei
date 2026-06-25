"""Authentication DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.schemas.common import ORMBase


class UserRead(ORMBase):
    id: uuid.UUID
    github_id: int
    username: str
    display_name: str | None
    email: str | None
    avatar_url: str | None


class DevLoginRequest(BaseModel):
    """Dev-only password-less login by GitHub-style handle."""

    username: str = "dev-user"
