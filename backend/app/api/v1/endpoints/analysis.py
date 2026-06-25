"""Analysis-job endpoints — trigger, status, history, SSE progress."""
from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, status
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import AnalysisServiceDep, verify_repository_access
from app.models.analysis_job import AnalysisJobStatus
from app.observability.metrics import analysis_jobs_enqueued_total
from app.schemas.analysis import AnalysisJobRead, AnalysisProgressEvent

router = APIRouter(
    prefix="/repositories/{repository_id}",
    tags=["analysis"],
    dependencies=[Depends(verify_repository_access)],
)


@router.post(
    "/analyze",
    response_model=AnalysisJobRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="(Re-)trigger analysis for an existing repository",
)
async def trigger_analysis(
    repository_id: uuid.UUID,
    service: AnalysisServiceDep,
) -> AnalysisJobRead:
    job = await service.trigger(repository_id)
    analysis_jobs_enqueued_total.inc()
    return AnalysisJobRead.model_validate(job)


@router.get(
    "/jobs",
    response_model=list[AnalysisJobRead],
    summary="List recent analysis jobs",
)
async def list_jobs(
    repository_id: uuid.UUID,
    service: AnalysisServiceDep,
) -> list[AnalysisJobRead]:
    jobs = await service.list_jobs(repository_id)
    return [AnalysisJobRead.model_validate(j) for j in jobs]


@router.get(
    "/jobs/latest",
    response_model=AnalysisJobRead,
    summary="Fetch the most recent analysis job for a repository",
)
async def latest_job(
    repository_id: uuid.UUID,
    service: AnalysisServiceDep,
) -> AnalysisJobRead:
    job = await service.latest_job_for_repository(repository_id)
    return AnalysisJobRead.model_validate(job)


@router.get(
    "/events",
    summary="Stream analysis progress events (SSE)",
)
async def stream_events(
    repository_id: uuid.UUID,
    service: AnalysisServiceDep,
) -> EventSourceResponse:
    async def event_publisher() -> AsyncIterator[dict[str, str]]:
        terminal = {
            AnalysisJobStatus.SUCCEEDED,
            AnalysisJobStatus.FAILED,
            AnalysisJobStatus.CANCELLED,
        }
        # Initial snapshot
        job = await service.latest_job_for_repository(repository_id)
        yield _serialize(job)

        # Poll every 1s until terminal or client disconnects.
        while job.status not in terminal:
            await asyncio.sleep(1.0)
            job = await service.get_job(job.id)
            yield _serialize(job)
        yield _serialize(job, final=True)

    return EventSourceResponse(event_publisher())


def _serialize(job, *, final: bool = False) -> dict[str, str]:
    event_name = {
        AnalysisJobStatus.QUEUED: "queued",
        AnalysisJobStatus.RUNNING: "running",
        AnalysisJobStatus.SUCCEEDED: "succeeded",
        AnalysisJobStatus.FAILED: "failed",
        AnalysisJobStatus.CANCELLED: "failed",
    }[job.status]
    if not final and job.status == AnalysisJobStatus.RUNNING:
        event_name = "progress"
    payload = AnalysisProgressEvent(
        event=event_name,  # type: ignore[arg-type]
        repository_id=job.repository_id,
        job_id=job.id,
        progress=job.progress,
        message=job.progress_message,
        error=job.error,
    )
    return {"event": event_name, "data": payload.model_dump_json()}
