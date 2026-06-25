"""Star model — a user's "star" on a repository (GitHub-style appreciation).

A star is a join row between a :class:`User` and a :class:`Repository`. Each
(user, repository) pair may exist at most once — re-starring is idempotent,
enforced by a unique constraint rather than application-level guesswork.

Semantics (enforced in the service/endpoint layer):
a user may star any repository they can *read* (their own, or any public one).
Star counts are public information for anyone who can see the repository.
Deleting either the user or the repository cascades the star away.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository
    from app.models.user import User


class Star(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "stars"
    __table_args__ = (
        # A user can star a given repository at most once.
        UniqueConstraint("user_id", "repository_id", name="uq_stars_user_repository"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Relationships (no back-populates: stars are a thin join, queried directly).
    user: Mapped["User"] = relationship()
    repository: Mapped["Repository"] = relationship()
