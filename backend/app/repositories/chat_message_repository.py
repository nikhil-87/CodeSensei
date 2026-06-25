"""Chat message data access."""
from __future__ import annotations

import uuid

from sqlalchemy import asc, func, select

from app.models.chat_message import ChatMessage
from app.repositories.base import BaseRepository


class ChatMessageRepository(BaseRepository[ChatMessage]):
    model = ChatMessage

    async def list_for_session(
        self,
        *,
        session_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[ChatMessage], int]:
        """Messages for a session, oldest first (chronological transcript)."""
        base = select(ChatMessage).where(ChatMessage.session_id == session_id)
        count_stmt = select(func.count()).select_from(base.subquery())
        rows = await self.session.execute(
            base.order_by(asc(ChatMessage.created_at)).limit(limit).offset(offset)
        )
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return list(rows.scalars().all()), total

    async def recent_for_session(
        self, *, session_id: uuid.UUID, limit: int
    ) -> list[ChatMessage]:
        """The most-recent ``limit`` messages, returned in chronological order.

        Used to build the LLM context window without loading an unbounded
        history into memory or the prompt.
        """
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        rows = await self.session.execute(stmt)
        messages = list(rows.scalars().all())
        messages.reverse()
        return messages
