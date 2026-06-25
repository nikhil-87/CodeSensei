"""SourceFile data access."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.source_file import SourceFile
from app.repositories.base import BaseRepository


class SourceFileRepository(BaseRepository[SourceFile]):
    model = SourceFile

    async def list_for_repository(
        self,
        repository_id: uuid.UUID,
        *,
        language: str | None = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> list[SourceFile]:
        stmt = select(SourceFile).where(SourceFile.repository_id == repository_id)
        if language is not None:
            stmt = stmt.where(SourceFile.language == language)
        stmt = stmt.order_by(SourceFile.path).limit(limit).offset(offset)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_path(
        self,
        repository_id: uuid.UUID,
        path: str,
    ) -> SourceFile | None:
        stmt = select(SourceFile).where(
            SourceFile.repository_id == repository_id,
            SourceFile.path == path,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def language_breakdown(
        self,
        repository_id: uuid.UUID,
    ) -> dict[str, int]:
        stmt = (
            select(SourceFile.language, func.count(SourceFile.id))
            .where(SourceFile.repository_id == repository_id)
            .group_by(SourceFile.language)
        )
        result = await self.session.execute(stmt)
        return {row[0]: int(row[1]) for row in result.all()}
