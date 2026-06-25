"""Symbol data access."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.models.source_file import SourceFile
from app.models.symbol import Symbol, SymbolKind
from app.repositories.base import BaseRepository


class SymbolRepository(BaseRepository[Symbol]):
    model = Symbol

    async def list_unused_for_repository(
        self,
        repository_id: uuid.UUID,
        *,
        limit: int = 500,
    ) -> list[tuple[Symbol, SourceFile]]:
        stmt = (
            select(Symbol, SourceFile)
            .join(SourceFile, Symbol.file_id == SourceFile.id)
            .where(
                SourceFile.repository_id == repository_id,
                Symbol.is_used.is_(False),
            )
            .order_by(SourceFile.path, Symbol.line_start)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def kind_counts_for_repository(
        self,
        repository_id: uuid.UUID,
    ) -> dict[SymbolKind, int]:
        stmt = (
            select(Symbol.kind, func.count(Symbol.id))
            .join(SourceFile, Symbol.file_id == SourceFile.id)
            .where(SourceFile.repository_id == repository_id)
            .group_by(Symbol.kind)
        )
        result = await self.session.execute(stmt)
        return {row[0]: int(row[1]) for row in result.all()}
