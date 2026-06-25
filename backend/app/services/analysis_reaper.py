"""Stuck-job reaper — fails analysis jobs whose worker has died.

Problem this solves
-------------------
A job moves to ``RUNNING`` and the worker then crashes (OOM, deploy, network
partition). The job stays ``RUNNING`` forever, and because of the
``uq_active_job_per_repository`` partial unique index, the repository can never
be re-analyzed — it is permanently stuck.

The same lifecycle systems use (GitHub Actions, Jenkins, K8s Jobs, Airflow):
a heartbeat plus a timeout. The worker writes ``heartbeat_at`` as it makes
progress; this reaper marks any job whose heartbeat has gone stale (or any
``QUEUED`` job that was never picked up) as ``FAILED`` and flips the repository
back to ``FAILED`` so the user can retry and the unique index frees up.

The reaper runs as a periodic backend background task (plus a one-shot sweep at
startup, which clears jobs orphaned by the very crash that restarted the app).
It is safe to run on multiple instances: the UPDATEs are atomic and idempotent.
"""
from __future__ import annotations

import asyncio
import contextlib

import structlog
from sqlalchemy import text

from app.core.config import Settings
from app.db.session import get_session_factory

logger = structlog.get_logger(__name__)


async def reap_stale_jobs(settings: Settings) -> int:
    """Fail stale RUNNING/QUEUED jobs and unblock their repositories.

    Returns the number of jobs reaped. Never raises — a failure here must not
    take down the background loop.
    """
    running_timeout = settings.analysis_running_heartbeat_timeout_seconds
    queued_timeout = settings.analysis_queued_timeout_seconds
    factory = get_session_factory(settings)

    try:
        async with factory() as session:
            # Fail RUNNING jobs whose worker stopped heartbeating, and QUEUED
            # jobs that were never picked up. COALESCE falls back through the
            # available timestamps so a NULL heartbeat (older rows) still ages out.
            result = await session.execute(
                text(
                    """
                    UPDATE analysis_jobs
                    SET status = 'failed',
                        completed_at = now(),
                        progress_message = 'failed',
                        error = CASE
                            WHEN status = 'running'
                                THEN 'worker_timeout: no heartbeat within '
                                     || :running_timeout || 's'
                            ELSE 'queue_timeout: job was not started within '
                                 || :queued_timeout || 's'
                        END
                    WHERE (
                        status = 'running'
                        AND now() - COALESCE(heartbeat_at, started_at, queued_at)
                            > make_interval(secs => :running_timeout)
                    ) OR (
                        status = 'queued'
                        AND now() - queued_at
                            > make_interval(secs => :queued_timeout)
                    )
                    RETURNING repository_id;
                    """
                ),
                {
                    "running_timeout": running_timeout,
                    "queued_timeout": queued_timeout,
                },
            )
            repo_ids = [row[0] for row in result.fetchall()]

            if repo_ids:
                # Unblock the repositories: flip any that are still mid-analysis
                # back to FAILED so the UI shows a retry path. READY repos that
                # had a failed *re*-analysis keep their last good state.
                await session.execute(
                    text(
                        """
                        UPDATE repositories
                        SET status = 'failed',
                            error_message = 'Analysis stopped responding and was '
                                            'timed out. Please try again.'
                        WHERE id = ANY(:repo_ids)
                          AND status IN ('pending', 'cloning', 'analyzing');
                        """
                    ),
                    {"repo_ids": repo_ids},
                )

            await session.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("reaper_sweep_failed", error=str(exc))
        return 0

    if repo_ids:
        logger.warning(
            "reaped_stale_jobs",
            count=len(repo_ids),
            repository_ids=[str(r) for r in repo_ids],
        )
    return len(repo_ids)


async def run_reaper_loop(settings: Settings) -> None:
    """Background loop: sweep immediately, then every ``interval`` seconds.

    Designed to be launched with ``asyncio.create_task`` from the app lifespan
    and cancelled on shutdown.
    """
    interval = max(10, settings.analysis_reaper_interval_seconds)
    logger.info("reaper_started", interval_seconds=interval)
    # Immediate startup sweep: clears jobs orphaned by the crash that may have
    # just restarted this very process.
    await reap_stale_jobs(settings)
    try:
        while True:
            await asyncio.sleep(interval)
            await reap_stale_jobs(settings)
    except asyncio.CancelledError:
        logger.info("reaper_stopped")
        raise
    except Exception as exc:  # noqa: BLE001 — keep the loop alive across blips
        logger.warning("reaper_loop_error", error=str(exc))
        with contextlib.suppress(asyncio.CancelledError):
            await asyncio.sleep(interval)
        await run_reaper_loop(settings)
