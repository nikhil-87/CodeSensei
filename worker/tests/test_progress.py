"""Tests for :class:`DbProgressReporter` + job lifecycle helpers."""
from __future__ import annotations

from app.models.analysis_job import AnalysisJobStatus  # noqa: F401
from worker.app.progress import (
    DbProgressReporter,
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
)


def test_stage_sets_initial_band_progress(make_repo, make_job, session_factory):
    repo = make_repo()
    job = make_job(repo.id)

    reporter = DbProgressReporter(job.id, session_factory=session_factory)
    reporter.stage("clone")

    with session_factory() as session:
        from app.models.analysis_job import AnalysisJob

        refreshed = session.get(AnalysisJob, job.id)
        assert refreshed.progress == 0  # clone band starts at 0
        assert "clone" in (refreshed.progress_message or "")


def test_progress_clamps_to_stage_band(make_repo, make_job, session_factory):
    repo = make_repo()
    job = make_job(repo.id)

    reporter = DbProgressReporter(job.id, session_factory=session_factory)
    reporter.stage("parse")  # band 20..60
    reporter.progress(0.5, message="halfway")

    with session_factory() as session:
        from app.models.analysis_job import AnalysisJob

        refreshed = session.get(AnalysisJob, job.id)
        # 0.5 between 20 and 60 → 40
        assert refreshed.progress == 40
        assert refreshed.progress_message == "halfway"


def test_progress_does_not_slide_backwards(make_repo, make_job, session_factory):
    repo = make_repo()
    job = make_job(repo.id)

    reporter = DbProgressReporter(job.id, session_factory=session_factory)
    reporter.stage("parse")
    reporter.progress(0.9)  # ~56
    reporter.stage("graph")  # band starts at 60 → 60 ≥ 56, ok

    with session_factory() as session:
        from app.models.analysis_job import AnalysisJob

        refreshed = session.get(AnalysisJob, job.id)
        assert refreshed.progress >= 56

    # An out-of-band ``progress(0.0)`` call must not slide back to 60.
    reporter.progress(0.0)
    with session_factory() as session:
        from app.models.analysis_job import AnalysisJob

        refreshed = session.get(AnalysisJob, job.id)
        assert refreshed.progress >= 60


def test_file_done_throttles_message_writes(make_repo, make_job, session_factory):
    repo = make_repo()
    job = make_job(repo.id)

    reporter = DbProgressReporter(
        job.id, throttle_files=3, session_factory=session_factory
    )
    reporter.stage("parse")
    for i in range(7):
        reporter.file_done(f"f{i}.py")

    with session_factory() as session:
        from app.models.analysis_job import AnalysisJob

        refreshed = session.get(AnalysisJob, job.id)
        # On 6th file (3 * 2) we wrote a message containing the file count.
        assert "6 files" in (refreshed.progress_message or "")


def test_mark_job_running_sets_status_and_started_at(
    make_repo, make_job, session_factory
):
    repo = make_repo()
    job = make_job(repo.id)

    mark_job_running(job.id, rq_job_id="rq-123", session_factory=session_factory)

    with session_factory() as session:
        from app.models.analysis_job import AnalysisJob, AnalysisJobStatus

        refreshed = session.get(AnalysisJob, job.id)
        assert refreshed.status == AnalysisJobStatus.RUNNING
        assert refreshed.started_at is not None
        assert refreshed.rq_job_id == "rq-123"


def test_mark_job_succeeded_sets_terminal_state(make_repo, make_job, session_factory):
    repo = make_repo()
    job = make_job(repo.id)

    mark_job_succeeded(job.id, session_factory=session_factory)

    with session_factory() as session:
        from app.models.analysis_job import AnalysisJob, AnalysisJobStatus

        refreshed = session.get(AnalysisJob, job.id)
        assert refreshed.status == AnalysisJobStatus.SUCCEEDED
        assert refreshed.progress == 100
        assert refreshed.completed_at is not None
        assert refreshed.error is None


def test_mark_job_failed_records_truncated_error(
    make_repo, make_job, session_factory
):
    repo = make_repo()
    job = make_job(repo.id)

    long_error = "X" * 6000
    mark_job_failed(job.id, error=long_error, session_factory=session_factory)

    with session_factory() as session:
        from app.models.analysis_job import AnalysisJob, AnalysisJobStatus

        refreshed = session.get(AnalysisJob, job.id)
        assert refreshed.status == AnalysisJobStatus.FAILED
        assert refreshed.error is not None
        assert len(refreshed.error) <= 4000


def test_progress_methods_swallow_db_errors(make_repo, make_job, session_factory):
    """Progress reporting must never crash a job on DB outage."""
    repo = make_repo()
    job = make_job(repo.id)

    class BrokenFactory:
        def __call__(self):  # type: ignore[no-untyped-def]
            raise RuntimeError("simulated DB outage")

    reporter = DbProgressReporter(job.id, session_factory=BrokenFactory())
    # None of these should raise.
    reporter.stage("parse")
    reporter.progress(0.5)
    reporter.file_done("foo.py")
