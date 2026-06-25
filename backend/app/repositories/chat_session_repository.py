"""Chat session data access.

All queries that fetch a session are *owner-scoped*: callers pass the
authenticated ``user_id`` and we filter on it in SQL, so a row belonging to
another user is simply never returned (the service turns that into a 404).
"""
from __future__ import annotations

import uuid

from sqlalchemy import delete, desc, func, select

from app.models.chat_session import ChatSession
from app.repositories.base import BaseRepository


class ChatSessionRepository(BaseRepository[ChatSession]):
    model = ChatSession

    async def get_owned(
        self, session_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> ChatSession | None:
        """Fetch a session only if it belongs to ``user_id``; else ``None``."""
        stmt = select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.user_id == user_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_repository(
        self,
        *,
        user_id: uuid.UUID,
        repository_id: uuid.UUID,
        limit: int,
        offset: int,
    ) -> tuple[list[ChatSession], int]:
        """A user's sessions for one repository, most-recent activity first."""
        base = select(ChatSession).where(
            ChatSession.user_id == user_id,
            ChatSession.repository_id == repository_id,
        )
        count_stmt = select(func.count()).select_from(base.subquery())
        rows = await self.session.execute(
            base.order_by(desc(ChatSession.last_activity_at)).limit(limit).offset(offset)
        )
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return list(rows.scalars().all()), total

    async def delete_owned(
        self, session_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> bool:
        """Delete a session if owned. Returns True if a row was removed."""
        stmt = (
            delete(ChatSession)
            .where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id,
            )
            .returning(ChatSession.id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
