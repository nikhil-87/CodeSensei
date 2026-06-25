"""AnalysisService — managing job lifecycle (status, re-trigger, cancel)."""
from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime

from app.core.exceptions import (
    AnalysisAlreadyRunningError,
    AnalysisJobNotFoundError,
    RepositoryNotFoundError,
)
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.repositories.analysis_job_repository import AnalysisJobRepository
from app.repositories.repository_repository import RepositoryRepository
from app.workers.job_dispatcher import JobDispatcher


class AnalysisService:
    def __init__(
        self,
        repository_repo: RepositoryRepository,
        job_repo: AnalysisJobRepository,
        dispatcher: JobDispatcher,
    ) -> None:
        self._repos = repository_repo
        self._jobs = job_repo
        self._dispatcher = dispatcher

    async def trigger(self, repository_id: uuid.UUID) -> AnalysisJob:
        repo = await self._repos.get(repository_id)
        if repo is None:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")
        if await self._jobs.has_active_job(repository_id):
            raise AnalysisAlreadyRunningError(
                f"Repository {repository_id} already has a running analysis"
            )

        job = AnalysisJob(
            repository_id=repository_id,
            status=AnalysisJobStatus.QUEUED,
            queued_at=datetime.now(UTC),
        )
        # add_active enforces one active job per repo at the DB level, closing
        # the race between the has_active_job check above and this insert.
        job = await self._jobs.add_active(job)
        job.rq_job_id = self._dispatcher.enqueue_analysis(repository_id, job.id)
        return job

    async def get_job(self, job_id: uuid.UUID) -> AnalysisJob:
        job = await self._jobs.get(job_id)
        if job is None:
            raise AnalysisJobNotFoundError(f"Job {job_id} not found")
        return job

    async def latest_job_for_repository(self, repository_id: uuid.UUID) -> AnalysisJob:
        job = await self._jobs.latest_for_repository(repository_id)
        if job is None:
            raise AnalysisJobNotFoundError(
                f"No analysis jobs for repository {repository_id}"
            )
        return job

    async def list_jobs(self, repository_id: uuid.UUID) -> list[AnalysisJob]:
        return await self._jobs.list_for_repository(repository_id)

    async def poll_until_terminal(
        self,
        job_id: uuid.UUID,
        *,
        interval_seconds: float = 1.0,
        timeout_seconds: float = 1800.0,
    ) -> AnalysisJob:
        """Polling helper for the SSE endpoint. Returns when terminal or on timeout.

        We poll the DB rather than using Redis pub/sub to keep dependencies
        minimal. A pub/sub channel is on the roadmap; documented as such.
        """
        elapsed = 0.0
        terminal = {
            AnalysisJobStatus.SUCCEEDED,
            AnalysisJobStatus.FAILED,
            AnalysisJobStatus.CANCELLED,
        }
        while elapsed < timeout_seconds:
            job = await self.get_job(job_id)
            if job.status in terminal:
                return job
            await asyncio.sleep(interval_seconds)
            elapsed += interval_seconds
        return await self.get_job(job_id)
