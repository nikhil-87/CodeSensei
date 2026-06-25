"""AnalysisJob data access."""
from __future__ import annotations

import uuid

from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AnalysisAlreadyRunningError
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.repositories.base import BaseRepository


class AnalysisJobRepository(BaseRepository[AnalysisJob]):
    model = AnalysisJob

    async def add_active(self, job: AnalysisJob) -> AnalysisJob:
        """Insert a QUEUED/RUNNING job, enforcing one-active-per-repo at the DB.

        A partial unique index (uq_active_job_per_repository) guarantees only a
        single active job per repository. If a concurrent request already
        created one, the flush raises ``IntegrityError`` which we translate to a
        clean ``analysis_already_running`` 409 — closing the check-then-act race
        that the prior ``has_active_job`` check alone could not.
        """
        self.session.add(job)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            await self.session.rollback()
            raise AnalysisAlreadyRunningError(
                "This repository is already being analyzed.",
                details={"repository_id": str(job.repository_id)},
            ) from exc
        await self.session.refresh(job)
        return job

    async def list_for_repository(
        self,
        repository_id: uuid.UUID,
        *,
        limit: int = 20,
    ) -> list[AnalysisJob]:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.repository_id == repository_id)
            .order_by(desc(AnalysisJob.queued_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def latest_for_repository(
        self,
        repository_id: uuid.UUID,
    ) -> AnalysisJob | None:
        stmt = (
            select(AnalysisJob)
            .where(AnalysisJob.repository_id == repository_id)
            .order_by(desc(AnalysisJob.queued_at))
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_active_job(self, repository_id: uuid.UUID) -> bool:
        stmt = select(AnalysisJob.id).where(
            AnalysisJob.repository_id == repository_id,
            AnalysisJob.status.in_(
                (AnalysisJobStatus.QUEUED, AnalysisJobStatus.RUNNING)
            ),
        ).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None
