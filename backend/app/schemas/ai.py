"""AI assistant DTOs (chat + SSE token stream)."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

from shared.config import defaults


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=8192)


class ChatRequest(BaseModel):
    repository_id: uuid.UUID
    question: str = Field(min_length=1, max_length=4096)
    history: list[ChatMessage] = Field(default_factory=list, max_length=20)
    top_k: int = Field(default=defaults.AI_TOP_K_CHUNKS, ge=1, le=20)
    # Files the user explicitly tagged, retrieved by metadata filter so the
    # answer is grounded in the tagged file rather than fuzzy vector matches.
    attached_paths: list[str] = Field(default_factory=list, max_length=10)


class ChatCitation(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    symbol: str | None = None
    snippet: str


class ChatTokenEvent(BaseModel):
    """One SSE message on the AI chat stream."""

    event: Literal["token", "citations", "done", "error"]
    content: str | None = None
    citations: list[ChatCitation] | None = None
    error: str | None = None
