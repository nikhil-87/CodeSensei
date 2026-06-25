"""Persisting :class:`engine.ProgressReporter` events to ``AnalysisJob``.

The engine reports fine-grained progress (one ``file_done`` per file).
Translating every callback into a ``UPDATE analysis_jobs`` would dominate
the wall-clock cost on large repos. We bucket file events by a count
threshold and translate stage transitions immediately (they're rare).
"""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog

from worker.app.db import session_scope

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

logger = structlog.get_logger(__name__)


# Stage → coarse percentage. The fine-grained engine progress (0..1 within
# a stage) is mapped onto the spread between consecutive stages.
_STAGE_BANDS: dict[str, tuple[int, int]] = {
    "clone": (0, 10),
    "walk": (10, 20),
    "parse": (20, 60),
    "graph": (60, 70),
    "metrics": (70, 75),
    "dead_code": (75, 80),
    "architecture": (80, 85),
    "persist": (85, 92),
    "index": (92, 99),
    "done": (100, 100),
}


class DbProgressReporter:
    """Writes progress to the ``analysis_jobs`` row for ``job_id``.

    Implements :class:`engine.ports.ProgressReporter` (duck-typed via
    Protocol). Tests can pass a custom session factory.
    """

    def __init__(
        self,
        job_id: uuid.UUID,
        *,
        throttle_files: int = 25,
        session_factory: "sessionmaker[Session] | None" = None,
    ) -> None:
        self._job_id = job_id
        self._throttle_files = max(1, throttle_files)
        self._session_factory = session_factory
        self._files_seen_in_stage = 0
        self._current_stage: str | None = None

    # ------------------------------------------------------------------
    # ProgressReporter interface (matches engine.ports.ProgressReporter)
    # ------------------------------------------------------------------
    def stage(self, name: str, message: str | None = None) -> None:
        self._current_stage = name
        self._files_seen_in_stage = 0
        band_start, _ = _STAGE_BANDS.get(name, (0, 0))
        self._write(progress=band_start, message=message or f"{name} started")

    def progress(self, fraction: float, message: str | None = None) -> None:
        if self._current_stage is None:
            return
        band_start, band_end = _STAGE_BANDS.get(self._current_stage, (0, 100))
        clamped = max(0.0, min(1.0, float(fraction)))
        value = int(band_start + (band_end - band_start) * clamped)
        self._write(progress=value, message=message or self._current_stage)

    def file_done(self, path: str) -> None:
        if self._current_stage is None:
            return
        self._files_seen_in_stage += 1
        # The engine separately calls ``progress(fraction)`` during parsing
        # so we only refresh the message field every N files to avoid
        # thrashing the row.
        if self._files_seen_in_stage % self._throttle_files == 0:
            self._write_message(
                f"{self._current_stage}: {self._files_seen_in_stage} files"
            )

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------
    def _write(self, *, progress: int, message: str) -> None:
        progress = max(0, min(100, int(progress)))
        message = (message or "")[:500]
        try:
            with self._scope() as session:
                from app.models.analysis_job import AnalysisJob  # noqa: PLC0415

                job = session.get(AnalysisJob, self._job_id)
                if job is None:
                    return
                if progress > job.progress:
                    job.progress = progress
                job.progress_message = message
                # Heartbeat: proves the worker is alive so the reaper doesn't
                # mistake a long-running stage for a crash.
                job.heartbeat_at = datetime.now(UTC)
        except Exception as exc:  # noqa: BLE001 — progress must never crash a job
            logger.warning("progress_write_failed", error=str(exc))

    def _write_message(self, message: str) -> None:
        try:
            with self._scope() as session:
                from app.models.analysis_job import AnalysisJob  # noqa: PLC0415

                job = session.get(AnalysisJob, self._job_id)
                if job is not None:
                    job.progress_message = (message or "")[:500]
                    job.heartbeat_at = datetime.now(UTC)
        except Exception as exc:  # noqa: BLE001
            logger.debug("progress_message_failed", error=str(exc))

    def _scope(self):  # type: ignore[no-untyped-def]
        if self._session_factory is None:
            return session_scope()
        return _factory_scope(self._session_factory)


# ---------------------------------------------------------------------------
@contextmanager
def _factory_scope(factory):  # type: ignore[no-untyped-def]
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Job lifecycle helpers
# ---------------------------------------------------------------------------
def mark_job_running(
    job_id: uuid.UUID,
    *,
    rq_job_id: str | None = None,
    session_factory=None,  # type: ignore[no-untyped-def]
) -> None:
    """Move an AnalysisJob from QUEUED → RUNNING."""
    from app.models.analysis_job import AnalysisJob, AnalysisJobStatus  # noqa: PLC0415

    scope = _factory_scope(session_factory) if session_factory else session_scope()
    with scope as session:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            return
        job.status = AnalysisJobStatus.RUNNING
        job.started_at = datetime.now(UTC)
        job.heartbeat_at = datetime.now(UTC)
        if rq_job_id:
            job.rq_job_id = rq_job_id


def mark_job_succeeded(
    job_id: uuid.UUID,
    *,
    session_factory=None,  # type: ignore[no-untyped-def]
) -> None:
    from app.models.analysis_job import AnalysisJob, AnalysisJobStatus  # noqa: PLC0415

    scope = _factory_scope(session_factory) if session_factory else session_scope()
    with scope as session:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            return
        job.status = AnalysisJobStatus.SUCCEEDED
        job.completed_at = datetime.now(UTC)
        job.progress = 100
        job.progress_message = "completed"
        job.error = None


def mark_job_failed(
    job_id: uuid.UUID,
    *,
    error: str,
    session_factory=None,  # type: ignore[no-untyped-def]
) -> None:
    from app.models.analysis_job import AnalysisJob, AnalysisJobStatus  # noqa: PLC0415

    scope = _factory_scope(session_factory) if session_factory else session_scope()
    with scope as session:
        job = session.get(AnalysisJob, job_id)
        if job is None:
            return
        job.status = AnalysisJobStatus.FAILED
        job.completed_at = datetime.now(UTC)
        job.error = (error or "")[:4000]
        job.progress_message = "failed"
