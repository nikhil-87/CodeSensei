"""User model — an authenticated account (currently via GitHub OAuth)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "users"

    # Stable numeric GitHub account id — the identity we key on across logins.
    github_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, unique=True, index=True
    )
    username: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="owner_user",
        cascade="all, delete-orphan",
    )
