"""Async engine + session factory.

We keep a single engine per process and lazily build a session factory bound
to it. Tests can override `get_session_factory` via FastAPI dependency_overrides
to swap in an SQLite-backed engine.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings

# Process-wide caches. ``Settings`` is a Pydantic model and intentionally
# mutable (env-variable driven) so we cannot use ``functools.lru_cache``
# directly on the constructors below; we cache on the *DSN* instead, which
# is the only field that affects engine identity.
_ENGINES: dict[str, AsyncEngine] = {}
_SESSION_FACTORIES: dict[str, async_sessionmaker[AsyncSession]] = {}


def get_engine(settings: Settings) -> AsyncEngine:
    """Process-wide async engine, cached after first construction."""
    dsn = settings.postgres_dsn_async
    engine = _ENGINES.get(dsn)
    if engine is None:
        engine = create_async_engine(
            dsn,
            echo=False,
            pool_pre_ping=True,
            pool_size=settings.postgres_pool_size,
            max_overflow=settings.postgres_max_overflow,
            pool_recycle=1800,
        )
        _ENGINES[dsn] = engine
    return engine


def get_session_factory(settings: Settings) -> async_sessionmaker[AsyncSession]:
    dsn = settings.postgres_dsn_async
    factory = _SESSION_FACTORIES.get(dsn)
    if factory is None:
        factory = async_sessionmaker(
            get_engine(settings),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
        _SESSION_FACTORIES[dsn] = factory
    return factory


async def dispose_engine(settings: Settings) -> None:
    """Cleanly close the engine on app shutdown."""
    dsn = settings.postgres_dsn_async
    engine = _ENGINES.pop(dsn, None)
    _SESSION_FACTORIES.pop(dsn, None)
    if engine is not None:
        await engine.dispose()
