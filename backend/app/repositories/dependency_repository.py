"""Dependency edge data access."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import aliased

from app.models.dependency import Dependency
from app.models.source_file import SourceFile
from app.repositories.base import BaseRepository


class DependencyRepository(BaseRepository[Dependency]):
    model = Dependency

    async def list_for_repository(
        self,
        repository_id: uuid.UUID,
    ) -> list[Dependency]:
        # Join via the from_file table to scope edges to one repository.
        from_file = aliased(SourceFile)
        stmt = (
            select(Dependency)
            .join(from_file, Dependency.from_file_id == from_file.id)
            .where(from_file.repository_id == repository_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def incoming_for_file(self, file_id: uuid.UUID) -> list[Dependency]:
        stmt = select(Dependency).where(Dependency.to_file_id == file_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def outgoing_for_file(self, file_id: uuid.UUID) -> list[Dependency]:
        stmt = select(Dependency).where(Dependency.from_file_id == file_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
