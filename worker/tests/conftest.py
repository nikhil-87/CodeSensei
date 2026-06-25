"""Test fixtures.

Hermetic — uses sqlite in-memory for the DB. The backend models are
SQLAlchemy 2.0 mapped classes that work against any dialect. The
sqlite dialect doesn't support PostgreSQL UUID() / Numeric() identically,
so the conftest patches the few model columns that need it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Make the backend package importable. The worker package depends on
# `app.models.*` at runtime; in the test environment we add the backend
# folder to sys.path explicitly rather than installing it.
_ROOT = Path(__file__).resolve().parents[2]
_BACKEND = _ROOT / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))


@pytest.fixture
def sqlite_engine():  # type: ignore[no-untyped-def]
    """In-memory sqlite engine with the backend's metadata applied.

    The backend's models use Postgres types (UUID, Numeric) — sqlite
    accepts them via SQLAlchemy's compatibility layer, so we only need
    to bind the metadata.
    """
    from app.db.base import Base  # noqa: PLC0415
    from app.models import (  # noqa: PLC0415, F401  (import for side-effects)
        analysis_job,
        dependency,
        metric,
        repository,
        source_file,
        symbol,
    )

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def session_factory(sqlite_engine):  # type: ignore[no-untyped-def]
    return sessionmaker(
        bind=sqlite_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        class_=Session,
    )


@pytest.fixture
def db_session(session_factory):  # type: ignore[no-untyped-def]
    session = session_factory()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def make_repo(db_session):  # type: ignore[no-untyped-def]
    """Insert a Repository row and return it."""
    from app.models.repository import Repository, RepositoryStatus  # noqa: PLC0415

    def _factory(
        url: str = "https://github.com/octocat/Hello-World",
        branch: str | None = None,
    ):  # type: ignore[no-untyped-def]
        repo = Repository(
            url=url,
            branch=branch,
            name="Hello-World",
            owner="octocat",
            status=RepositoryStatus.PENDING,
        )
        db_session.add(repo)
        db_session.commit()
        db_session.refresh(repo)
        return repo

    return _factory


@pytest.fixture
def make_job(db_session):  # type: ignore[no-untyped-def]
    """Insert an AnalysisJob row and return it."""
    from datetime import UTC, datetime  # noqa: PLC0415

    from app.models.analysis_job import (  # noqa: PLC0415
        AnalysisJob,
        AnalysisJobStatus,
    )

    def _factory(repository_id):  # type: ignore[no-untyped-def]
        job = AnalysisJob(
            repository_id=repository_id,
            status=AnalysisJobStatus.QUEUED,
            queued_at=datetime.now(UTC),
        )
        db_session.add(job)
        db_session.commit()
        db_session.refresh(job)
        return job

    return _factory
