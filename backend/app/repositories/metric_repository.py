"""Metric data access."""
from __future__ import annotations

import statistics
import uuid

from sqlalchemy import desc, select

from app.models.metric import Metric
from app.models.source_file import SourceFile
from app.repositories.base import BaseRepository


class MetricRepository(BaseRepository[Metric]):
    model = Metric

    async def list_for_repository(
        self,
        repository_id: uuid.UUID,
    ) -> list[tuple[Metric, SourceFile]]:
        stmt = (
            select(Metric, SourceFile)
            .join(SourceFile, Metric.file_id == SourceFile.id)
            .where(SourceFile.repository_id == repository_id)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def top_complex(
        self,
        repository_id: uuid.UUID,
        *,
        limit: int = 10,
    ) -> list[tuple[Metric, SourceFile]]:
        stmt = (
            select(Metric, SourceFile)
            .join(SourceFile, Metric.file_id == SourceFile.id)
            .where(SourceFile.repository_id == repository_id)
            .order_by(desc(Metric.cyclomatic))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]

    async def averages(self, repository_id: uuid.UUID) -> dict[str, float]:
        """Aggregate metrics for a repository.

        We fetch the small per-file Metric rows and compute aggregates in
        Python rather than relying on dialect-specific window functions
        (e.g. PostgreSQL's ``percentile_cont``). This keeps the same code
        running on Postgres in production and on SQLite in tests.
        """
        stmt = (
            select(
                Metric.cyclomatic,
                Metric.cognitive,
                Metric.lines_of_code,
            )
            .join(SourceFile, Metric.file_id == SourceFile.id)
            .where(SourceFile.repository_id == repository_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()
        if not rows:
            return {"cyclomatic": 0.0, "cognitive": 0.0, "loc_median": 0.0}

        cyclomatics = [int(r[0] or 0) for r in rows]
        cognitives = [int(r[1] or 0) for r in rows]
        locs = [int(r[2] or 0) for r in rows]
        return {
            "cyclomatic": statistics.fmean(cyclomatics),
            "cognitive": statistics.fmean(cognitives),
            "loc_median": float(statistics.median(locs)),
        }
