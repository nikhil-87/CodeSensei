"""Chat message model — one turn in a :class:`ChatSession`.

We persist both the user's question and the assistant's answer. For assistant
turns we also store the citations the RAG pipeline returned; for user turns we
store the files that were attached as context at send time. Both are kept as
JSONB so reopening a session re-renders sources and context chips faithfully
without re-running the model.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.chat_session import ChatSession


class ChatMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # "user" | "assistant". System prompts are generated per-request and never
    # stored — they are an implementation detail of the engine.
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Assistant turns: the citations rendered beneath the answer.
    # Shape: list[{file_path, line_start, line_end, symbol?, snippet}].
    citations: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )
    # User turns: files attached as context. Shape: list[{path, language?}].
    attached_context: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB, nullable=True
    )

    session: Mapped["ChatSession"] = relationship(back_populates="messages")
