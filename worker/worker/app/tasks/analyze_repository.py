"""``analyze_repository`` — the main RQ task.

End-to-end flow:

    QUEUED → RUNNING
        ├─ stage(clone)        → engine.GitCloner          (worker drives it
        │                                                    so it knows the
        │                                                    target path)
        ├─ stage(walk/parse/…) → engine.AnalysisOrchestrator
        ├─ stage(persist)      → worker.persistence
        └─ stage(index)        → engine.ai.RagChain         (best-effort)
    RUNNING → SUCCEEDED  (FAILED on hard error)

Everything that can fail is wrapped so the job row is always closed out
with a deterministic terminal state.
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import structlog

from engine.cloning.git_cloner import CloneOptions, GitCloner
from engine.exceptions import EngineError
from engine.orchestrator import AnalysisOptions, AnalysisOrchestrator
from engine.results import RepositoryAnalysis
from worker.app.ai_runtime import (
    build_runtime,
    index_with_runtime,
    read_sources,
)
from worker.app.db import init_engine, session_scope
from worker.app.exceptions import IndexingDegraded
from worker.app.logging_config import configure_logging
from worker.app.metrics import (
    record_chunks_indexed,
    record_files_processed,
    record_job_outcome,
    track_analysis_job,
)
from worker.app.persistence import persist_repository_analysis
from worker.app.progress import (
    DbProgressReporter,
    mark_job_failed,
    mark_job_running,
    mark_job_succeeded,
)
from worker.app.settings import WorkerSettings, get_settings

logger = structlog.get_logger(__name__)


def run(
    repository_id: str,
    job_id: str,
    *,
    settings: WorkerSettings | None = None,
) -> dict[str, Any]:
    """Entry point. Signature must remain ``(repository_id, job_id)`` because
    the backend's :class:`JobDispatcher` enqueues with those exact kwargs.
    """
    cfg = settings or get_settings()
    configure_logging(cfg.app_log_level)
    init_engine(cfg)

    repo_uuid = uuid.UUID(repository_id)
    job_uuid = uuid.UUID(job_id)

    logger.info("analyze_started", repository_id=repository_id, job_id=job_id)
    mark_job_running(job_uuid)

    reporter = DbProgressReporter(
        job_uuid, throttle_files=cfg.worker_progress_throttle_files
    )

    with track_analysis_job():
        try:
            return _run_inner(cfg, repo_uuid, job_uuid, reporter)
        except EngineError as exc:
            logger.error("analyze_engine_error", error=str(exc), exc_info=True)
            _mark_failed(repo_uuid, job_uuid, str(exc))
            record_job_outcome(succeeded=False)
            raise
        except Exception as exc:  # noqa: BLE001 — re-raised after marking failed
            logger.error("analyze_unexpected_error", error=str(exc), exc_info=True)
            _mark_failed(repo_uuid, job_uuid, str(exc))
            record_job_outcome(succeeded=False)
            raise


def _run_inner(
    cfg: WorkerSettings,
    repo_uuid: uuid.UUID,
    job_uuid: uuid.UUID,
    reporter: DbProgressReporter,
) -> dict[str, Any]:
    repository_id = str(repo_uuid)
    job_id = str(job_uuid)

    # 1. Read repo URL/branch + flip Repository.status → analyzing.
    url, branch = _load_repo_url_and_mark_running(repo_uuid)

    # 2. Clone (we drive the cloner ourselves so we keep the path).
    reporter.stage("clone", f"Cloning {url}")
    cfg.workspace_root.mkdir(parents=True, exist_ok=True)
    cloner = GitCloner(
        CloneOptions(
            workspace_root=cfg.workspace_root,
            branch=branch,
            max_size_mb=cfg.api_max_repo_size_mb,
        )
    )
    workspace = cloner.clone(url)
    commit_hash = GitCloner.head_commit(workspace)
    if commit_hash:
        logger.info("clone_commit", repository_id=repository_id, commit=commit_hash)

    # 3. Analyse the cloned tree.
    orchestrator = AnalysisOrchestrator(
        AnalysisOptions(
            workspace_root=cfg.workspace_root,
            max_repo_size_mb=cfg.api_max_repo_size_mb,
            max_files=cfg.api_max_repo_files,
        ),
        reporter=reporter,
    )
    analysis = orchestrator.run_on_path(workspace)

    # 4. Persist into Postgres.
    reporter.stage("persist", f"Persisting {len(analysis.files)} files")
    with session_scope() as session:
        counts = persist_repository_analysis(
            session,
            repository_id=repo_uuid,
            analysis=analysis,
            commit_hash=commit_hash,
            embedding_model=cfg.embedding_signature,
        )
    record_files_processed(int(counts.get("files", 0)))

    # 5. Best-effort vector indexing.
    reporter.stage("index", "Indexing for AI search")
    indexed_chunks = 0
    if cfg.worker_indexing_enabled:
        indexed_chunks = _try_index(cfg, repo_uuid, analysis, workspace)
    record_chunks_indexed(indexed_chunks)

    # 6. Done.
    reporter.stage("done", "Analysis complete")
    mark_job_succeeded(job_uuid)
    record_job_outcome(succeeded=True)
    result = {
        "repository_id": repository_id,
        "job_id": job_id,
        **counts,
        "indexed_chunks": indexed_chunks,
    }
    logger.info("analyze_completed", **result)
    return result


# ---------------------------------------------------------------------------
def _load_repo_url_and_mark_running(
    repository_id: uuid.UUID,
) -> tuple[str, str | None]:
    from app.models.repository import Repository, RepositoryStatus  # noqa: PLC0415

    with session_scope() as session:
        repo = session.get(Repository, repository_id)
        if repo is None:
            raise ValueError(f"Repository {repository_id} not found")
        repo.status = RepositoryStatus.ANALYZING
        repo.error_message = None
        return repo.url, repo.branch


def _try_index(
    cfg: WorkerSettings,
    repository_id: uuid.UUID,
    analysis: RepositoryAnalysis,
    workspace: Path,
) -> int:
    runtime = build_runtime(cfg, repository_id)
    try:
        sources = read_sources(workspace, analysis.files)
        result = index_with_runtime(
            runtime,
            repository_id=repository_id,
            files=analysis.files,
            sources=sources,
        )
        return result.chunks_indexed
    except IndexingDegraded as exc:
        logger.warning("index_skipped", error=str(exc))
        return 0
    finally:
        try:
            runtime.ollama.close()
        except Exception:  # noqa: BLE001
            logger.debug("ollama_close_failed_silent")


def _mark_failed(
    repo_uuid: uuid.UUID, job_uuid: uuid.UUID, error: str
) -> None:
    """Mark both the job and the repository as failed (best-effort)."""
    try:
        mark_job_failed(job_uuid, error=error)
    except Exception as exc:  # noqa: BLE001
        logger.error("mark_job_failed_error", error=str(exc))

    try:
        from app.models.repository import Repository, RepositoryStatus  # noqa: PLC0415

        with session_scope() as session:
            repo = session.get(Repository, repo_uuid)
            if repo is not None:
                repo.status = RepositoryStatus.FAILED
                repo.error_message = error[:2000]
    except Exception as exc:  # noqa: BLE001
        logger.error("mark_repo_failed_error", error=str(exc))
