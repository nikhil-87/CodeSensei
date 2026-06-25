"""Star data access — the (user, repository) appreciation join."""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.repository import Repository
from app.models.star import Star
from app.repositories.base import BaseRepository


class StarRepository(BaseRepository[Star]):
    model = Star

    async def exists(self, *, user_id: uuid.UUID, repository_id: uuid.UUID) -> bool:
        stmt = select(Star.id).where(
            Star.user_id == user_id, Star.repository_id == repository_id
        )
        result = await self.session.execute(stmt)
        return result.first() is not None

    async def create_star(
        self, *, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> bool:
        """Idempotently record a star. Returns ``True`` if a new row was created.

        Uses ``INSERT ... ON CONFLICT DO NOTHING`` so concurrent first-stars by
        the same user collapse to a single row instead of raising a unique
        violation — the operation is safe to retry and cannot create duplicates.
        """
        stmt = (
            pg_insert(Star)
            .values(user_id=user_id, repository_id=repository_id)
            .on_conflict_do_nothing(
                index_elements=[Star.user_id, Star.repository_id]
            )
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(result.rowcount)


    async def delete_star(
        self, *, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> bool:
        """Remove a star if present. Returns ``True`` if a row was deleted."""
        stmt = delete(Star).where(
            Star.user_id == user_id, Star.repository_id == repository_id
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return bool(result.rowcount)

    async def count_for_repository(self, repository_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Star).where(
            Star.repository_id == repository_id
        )
        result = await self.session.execute(stmt)
        return int(result.scalar_one())

    async def starred_repository_ids(
        self, *, user_id: uuid.UUID, repository_ids: Sequence[uuid.UUID]
    ) -> set[uuid.UUID]:
        """Of ``repository_ids``, return the subset this user has starred.

        A single batched query that backs the ``viewer_has_starred`` flag on
        list responses without an N+1 per-row lookup.
        """
        if not repository_ids:
            return set()
        stmt = select(Star.repository_id).where(
            Star.user_id == user_id, Star.repository_id.in_(repository_ids)
        )
        result = await self.session.execute(stmt)
        return set(result.scalars().all())

    async def list_starred(
        self, *, user_id: uuid.UUID, limit: int, offset: int
    ) -> tuple[list[Repository], int]:
        """Repositories the user has starred, most-recently-starred first."""
        base_stmt = (
            select(Repository)
            .join(Star, Star.repository_id == Repository.id)
            .where(Star.user_id == user_id)
            .order_by(desc(Star.created_at))
            .limit(limit)
            .offset(offset)
        )
        count_stmt = (
            select(func.count())
            .select_from(Star)
            .where(Star.user_id == user_id)
        )
        items = list((await self.session.execute(base_stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total
