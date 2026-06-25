"""Chat session + message DTOs (persistent AI conversations)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.ai import ChatCitation
from app.schemas.common import ORMBase


class AttachedContext(BaseModel):
    """A file attached to a message as grounding context."""

    path: str = Field(min_length=1, max_length=1024)
    language: str | None = Field(default=None, max_length=64)


class ChatSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)


class ChatSessionUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=200)


class ChatSessionRead(ORMBase):
    id: uuid.UUID
    repository_id: uuid.UUID
    title: str
    last_activity_at: datetime
    created_at: datetime
    updated_at: datetime


class ChatMessageRead(ORMBase):
    id: uuid.UUID
    session_id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    citations: list[ChatCitation] | None = None
    attached_context: list[AttachedContext] | None = None
    created_at: datetime


class SessionChatRequest(BaseModel):
    """Send a question within a session. The repository is taken from the
    session itself (never the client) so a session can't be redirected at
    another repo.
    """

    question: str = Field(min_length=1, max_length=4096)
    attached: list[AttachedContext] = Field(default_factory=list, max_length=10)
    top_k: int = Field(default=8, ge=1, le=20)
