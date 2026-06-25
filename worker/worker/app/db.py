"""Synchronous SQLAlchemy session factory used by RQ tasks.

RQ workers run in OS threads with a synchronous control flow. Mirroring
the backend's async session would mean spinning up an event loop per
task — slower and harder to reason about. Instead we use a *separate*
synchronous engine bound to the same models.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from threading import Lock
from typing import TYPE_CHECKING

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

if TYPE_CHECKING:
    from worker.app.settings import WorkerSettings


_engine_lock = Lock()
_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def init_engine(settings: "WorkerSettings", *, dsn: str | None = None) -> Engine:
    """Create the singleton sync engine. Idempotent."""
    global _engine, _SessionFactory
    with _engine_lock:
        if _engine is not None:
            return _engine
        url = dsn or settings.postgres_dsn_sync
        _engine = create_engine(
            url,
            pool_size=settings.postgres_pool_size,
            pool_pre_ping=True,
            future=True,
        )
        _SessionFactory = sessionmaker(
            bind=_engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        return _engine


def get_session_factory() -> sessionmaker[Session]:
    if _SessionFactory is None:
        raise RuntimeError(
            "Session factory is not initialised; call init_engine(settings) first."
        )
    return _SessionFactory


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def reset_for_tests(
    engine: Engine | None,
    session_factory: "sessionmaker[Session] | None",
) -> None:
    """Test hook — replaces the module globals with caller-provided ones."""
    global _engine, _SessionFactory
    _engine = engine
    _SessionFactory = session_factory
