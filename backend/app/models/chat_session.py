"""Chat session model — a persistent, user-private AI conversation.

A session is owned by exactly one user and scoped to exactly one repository.

Privacy invariant (enforced in the service/endpoint layer, never relaxed):
chat sessions are visible ONLY to ``user_id``. This holds even when the
underlying repository is public — a public *analysis* never implies a public
*conversation*. Cross-user access is hidden behind a 404 (IDOR-safe).
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import uuid

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chat_message import ChatMessage
    from app.models.repository import Repository
    from app.models.user import User


class ChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_sessions"
    __table_args__ = (
        # The hot query: "list MY sessions for THIS repo, most-recent first".
        Index(
            "ix_chat_sessions_user_repo_activity",
            "user_id",
            "repository_id",
            "last_activity_at",
        ),
    )

    # Owner of the conversation. Deleting the user removes their sessions.
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Repository the conversation is grounded in. Deleting the repo (or its
    # analysis) removes the now-meaningless conversations.
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(200), nullable=False, default="New chat", server_default="New chat"
    )
    # Distinct from updated_at: bumped on every message so the session list can
    # sort by genuine conversational activity (a rename shouldn't reorder it).
    last_activity_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship()
    repository: Mapped["Repository"] = relationship()
    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )
