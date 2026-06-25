"""End-to-end test of the RQ task in isolation.

We monkey-patch :class:`GitCloner` and :class:`AnalysisOrchestrator`
to avoid touching the network or doing real parsing, and we replace
``build_runtime`` with a fake to exercise the indexing branch.

The point: prove that the task properly sets job status, repo status,
persists results, and stays SUCCEEDED even when indexing degrades.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from engine.results import (
    ArchitectureLayer,
    ArchitectureReport,
    DependencyEdge,
    FileAnalysis,
    FileMetrics,
    RepositoryAnalysis,
    Symbol,
)
from worker.app import db as db_module
from worker.app.exceptions import IndexingDegraded
from worker.app.tasks import analyze_repository
from worker.app.settings import WorkerSettings


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _fake_analysis() -> RepositoryAnalysis:
    files = (
        FileAnalysis(
            path="src/a.py",
            language="python",
            size_bytes=120,
            line_count=12,
            sha256="0" * 64,
            symbols=(Symbol("foo", "function", 1, 5),),
            imports=(),
            metrics=FileMetrics(
                cyclomatic=1, cognitive=1, lines_of_code=12, function_count=1, class_count=0
            ),
            parser="python_ast",
        ),
    )
    return RepositoryAnalysis(
        files=files,
        dependencies=(),
        cycles=(),
        languages={"python": 1},
        total_lines=12,
        dead_code=(),
        architecture=ArchitectureReport(
            layers=(ArchitectureLayer(name="services", file_paths=("src/a.py",)),),
            violations=(),
            mermaid="graph TD",
        ),
    )


class _FakeOllama:
    def close(self) -> None:  # noqa: D401
        pass


class _FakeChain:
    def __init__(self) -> None:
        self.indexed = False

    def index_repository(self, files, sources):  # type: ignore[no-untyped-def]
        self.indexed = True
        from engine.ai import IndexingResult

        return IndexingResult(
            chunks_indexed=4, files_indexed=len(files), files_skipped=0
        )


class _FakeVectorStore:
    def __init__(self) -> None:
        self.deleted = False

    def delete_collection(self) -> None:
        self.deleted = True


class _FakeRuntime:
    def __init__(self) -> None:
        self.chain = _FakeChain()
        self.ollama = _FakeOllama()
        self.vector_store = _FakeVectorStore()


@pytest.fixture
def patched_engine(monkeypatch, tmp_path):  # type: ignore[no-untyped-def]
    """Patch GitCloner + AnalysisOrchestrator + AI runtime."""
    fake_workspace = tmp_path / "ws"
    fake_workspace.mkdir(parents=True)
    (fake_workspace / "src").mkdir()
    (fake_workspace / "src" / "a.py").write_text("def foo(): pass\n")

    class FakeCloner:
        def __init__(self, options) -> None:  # noqa: ANN001
            self.options = options

        def clone(self, url: str) -> Path:  # noqa: ARG002, D401
            return fake_workspace

    class FakeOrchestrator:
        def __init__(self, options, reporter=None) -> None:  # noqa: ANN001
            self.options = options
            self.reporter = reporter

        def run_on_path(self, path: Path) -> RepositoryAnalysis:  # noqa: ARG002
            if self.reporter is not None:
                self.reporter.stage("parse")
                self.reporter.progress(0.5)
            return _fake_analysis()

    monkeypatch.setattr(analyze_repository, "GitCloner", FakeCloner)
    monkeypatch.setattr(analyze_repository, "AnalysisOrchestrator", FakeOrchestrator)
    monkeypatch.setattr(
        analyze_repository, "build_runtime", lambda *a, **k: _FakeRuntime()
    )
    return fake_workspace


@pytest.fixture
def settings(tmp_path) -> WorkerSettings:  # type: ignore[no-untyped-def]
    """Create test settings using shared test configuration."""
    try:
        from shared.config.testing import make_test_worker_settings
        config = make_test_worker_settings(tmp_path)
    except ImportError:
        # Fallback if shared module not available
        config = {
            "postgres_host": "localhost",
            "postgres_port": 5432,
            "postgres_user": "codesensei",
            "postgres_password": "codesensei",
            "postgres_db": "codesensei_test",
            "redis_host": "localhost",
            "redis_port": 6379,
            "redis_db": 0,
            "redis_queue_name": "codesensei:test",
            "chroma_host": "localhost",
            "chroma_port": 8000,
            "chroma_collection_prefix": "repo-",
            "ollama_base_url": "http://localhost:11434",
            "ollama_chat_model": "x",
            "ollama_embed_model": "y",
            "ollama_timeout_seconds": 10,
            "worker_clone_dir": str(tmp_path / "ws"),
            "api_max_repo_size_mb": 200,
            "api_max_repo_files": 500,
            "worker_progress_throttle_files": 5,
            "worker_indexing_enabled": True,
            "app_log_level": "WARNING",
        }
    return WorkerSettings(**config)


@pytest.fixture
def patched_db(monkeypatch, sqlite_engine, session_factory):  # type: ignore[no-untyped-def]
    """Bypass init_engine — bind module globals to the sqlite engine."""
    db_module.reset_for_tests(sqlite_engine, session_factory)
    monkeypatch.setattr(
        analyze_repository, "init_engine", lambda *a, **k: sqlite_engine
    )
    monkeypatch.setattr(analyze_repository, "configure_logging", lambda *a, **k: None)
    yield
    db_module.reset_for_tests(None, None)


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------
def test_run_marks_job_succeeded_and_repo_ready(
    make_repo, make_job, settings, patched_engine, patched_db
):
    repo = make_repo()
    job = make_job(repo.id)

    result = analyze_repository.run(
        repository_id=str(repo.id), job_id=str(job.id), settings=settings
    )

    assert result["files"] == 1
    assert result["indexed_chunks"] == 4

    from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
    from app.models.repository import Repository, RepositoryStatus
    from app.models.source_file import SourceFile

    with db_module.session_scope() as session:
        refreshed_job = session.get(AnalysisJob, UUID(str(job.id)))
        refreshed_repo = session.get(Repository, UUID(str(repo.id)))
        files = session.query(SourceFile).filter_by(repository_id=repo.id).all()

        assert refreshed_job.status == AnalysisJobStatus.SUCCEEDED
        assert refreshed_job.progress == 100
        assert refreshed_repo.status == RepositoryStatus.READY
        assert len(files) == 1


def test_run_succeeds_even_when_indexing_fails(
    monkeypatch, make_repo, make_job, settings, patched_engine, patched_db
):
    repo = make_repo()
    job = make_job(repo.id)

    def boom(*a, **k):  # noqa: ANN001, ANN002, ARG001
        raise IndexingDegraded("ollama down")

    monkeypatch.setattr(analyze_repository, "index_with_runtime", boom)

    result = analyze_repository.run(
        repository_id=str(repo.id), job_id=str(job.id), settings=settings
    )

    assert result["indexed_chunks"] == 0

    from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
    from app.models.repository import Repository, RepositoryStatus

    with db_module.session_scope() as session:
        refreshed_job = session.get(AnalysisJob, UUID(str(job.id)))
        refreshed_repo = session.get(Repository, UUID(str(repo.id)))
        assert refreshed_job.status == AnalysisJobStatus.SUCCEEDED
        assert refreshed_repo.status == RepositoryStatus.READY


def test_run_marks_failure_on_engine_error(
    monkeypatch, make_repo, make_job, settings, patched_engine, patched_db
):
    repo = make_repo()
    job = make_job(repo.id)

    class FailingOrchestrator:
        def __init__(self, *a, **k) -> None:  # noqa: ANN001, ANN002
            pass

        def run_on_path(self, path: Path) -> RepositoryAnalysis:  # noqa: ARG002
            from engine.exceptions import EngineError

            raise EngineError("parser blew up")

    monkeypatch.setattr(
        analyze_repository, "AnalysisOrchestrator", FailingOrchestrator
    )

    with pytest.raises(Exception):  # noqa: B017
        analyze_repository.run(
            repository_id=str(repo.id), job_id=str(job.id), settings=settings
        )

    from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
    from app.models.repository import Repository, RepositoryStatus

    with db_module.session_scope() as session:
        refreshed_job = session.get(AnalysisJob, UUID(str(job.id)))
        refreshed_repo = session.get(Repository, UUID(str(repo.id)))
        assert refreshed_job.status == AnalysisJobStatus.FAILED
        assert refreshed_repo.status == RepositoryStatus.FAILED
        assert "parser blew up" in (refreshed_job.error or "")
