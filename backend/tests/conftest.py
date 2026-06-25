"""Pytest fixtures: in-memory SQLite (aiosqlite), fake Redis, FastAPI test client.

The production stack runs on Postgres + Redis; for unit/integration tests we
substitute lightweight equivalents so suites stay hermetic and fast.
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import fakeredis.aioredis

from app.cache.redis_cache import RedisCache
from app.core.config import Settings, get_settings
from app.core.dependencies import _make_job_dispatcher, get_cache, get_db_session
from app.db.base import Base
from app.main import create_app
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.models.dependency import Dependency, DependencyKind
from app.models.metric import Metric
from app.models.repository import Repository, RepositoryStatus
from app.models.source_file import SourceFile
from app.models.symbol import Symbol, SymbolKind
from app.models.user import User
from shared.config import defaults


# ---------------------------------------------------------------------------
# Test-only settings: SQLite + test markers.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    return Settings(
        app_env="test",
        app_secret_key="test-secret-key-must-be-at-least-32-characters-long",
        postgres_host="sqlite-in-memory",  # ignored — we override DSN below
        postgres_password="test",
        redis_host="fake",
        # Authenticate every request as the predefined mock user so the suite
        # exercises protected routes without real GitHub OAuth credentials.
        mock_auth=True,
    )


# ---------------------------------------------------------------------------
# Async engine + schema, recreated per test for isolation.
#
# We use StaticPool so every connection sees the same in-memory database —
# without it, each `aiosqlite` connection gets its own empty DB and seeded
# rows would be invisible to API requests.
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def db_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Fake job dispatcher — never touches Redis.
# ---------------------------------------------------------------------------
class FakeJobDispatcher:
    """In-memory stand-in for ``app.workers.job_dispatcher.JobDispatcher``.

    Records calls so tests can assert on them; ``enqueue_analysis`` returns
    a deterministic id so the seam between API ↔ queue is observable.
    """

    def __init__(self) -> None:
        self.enqueued: list[tuple[uuid.UUID, uuid.UUID]] = []

    def enqueue_analysis(self, repository_id: uuid.UUID, job_id: uuid.UUID) -> str:
        self.enqueued.append((repository_id, job_id))
        return f"rq:test:{job_id}"

    def queue_depth(self) -> int:
        return len(self.enqueued)

    def healthcheck(self) -> dict[str, Any]:
        return {"status": "ok", "queue_depth": self.queue_depth()}


@pytest.fixture
def fake_dispatcher() -> FakeJobDispatcher:
    return FakeJobDispatcher()


# ---------------------------------------------------------------------------
# Fake Redis cache — backed by `fakeredis` so JSON SET/GET behave realistically
# without requiring a live Redis server.
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_cache() -> RedisCache:
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    return RedisCache(client, default_ttl=60)


# ---------------------------------------------------------------------------
# FastAPI client with DB + dispatcher dependency overrides.
# ---------------------------------------------------------------------------
@pytest.fixture
def client(
    test_settings: Settings,
    db_engine: AsyncEngine,
    fake_dispatcher: FakeJobDispatcher,
    fake_cache: RedisCache,
) -> Iterator[TestClient]:
    app = create_app(test_settings)

    async def _override_session() -> AsyncIterator[AsyncSession]:
        factory = async_sessionmaker(db_engine, expire_on_commit=False)
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def _override_cache() -> RedisCache:
        return fake_cache

    app.dependency_overrides[get_db_session] = _override_session
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[_make_job_dispatcher] = lambda: fake_dispatcher
    app.dependency_overrides[get_cache] = _override_cache

    with TestClient(app) as test_client:
        yield test_client


# ---------------------------------------------------------------------------
# Test-data factories
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def mock_user(db_engine: AsyncEngine) -> User:
    """The predefined mock-auth user, persisted so owned rows satisfy FKs.

    Uses the same identity constants as ``Settings.mock_auth_*`` so the user
    created here is the exact row that ``get_optional_user`` resolves to when
    ``mock_auth`` is enabled (it upserts by ``github_id``).
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        user = User(
            github_id=defaults.MOCK_AUTH_GITHUB_ID,
            username=defaults.MOCK_AUTH_USERNAME,
            display_name=defaults.MOCK_AUTH_DISPLAY_NAME,
            email=defaults.MOCK_AUTH_EMAIL,
            avatar_url=defaults.MOCK_AUTH_AVATAR_URL,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def seeded_repository(db_engine: AsyncEngine, mock_user: User) -> Repository:
    """Insert a small but realistic repository graph for read-only API tests.

    Owned by the mock-auth user so owner-scoped endpoints return it.
    """
    factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with factory() as session:
        repo = Repository(
            owner_id=mock_user.id,
            url="https://github.com/octocat/Hello-World",
            branch="main",
            default_branch="main",
            name="Hello-World",
            owner="octocat",
            status=RepositoryStatus.READY,
            file_count=2,
            total_lines=100,
            languages="python:2",
            analyzed_at=datetime.now(UTC),
        )
        session.add(repo)
        await session.flush()

        file_a = SourceFile(
            repository_id=repo.id,
            path="src/a.py",
            language="python",
            line_count=60,
            size_bytes=2048,
        )
        file_b = SourceFile(
            repository_id=repo.id,
            path="src/b.py",
            language="python",
            line_count=40,
            size_bytes=1024,
        )
        session.add_all([file_a, file_b])
        await session.flush()

        session.add_all(
            [
                Metric(
                    file_id=file_a.id,
                    cyclomatic=14,
                    cognitive=18,
                    lines_of_code=55,
                    function_count=4,
                    class_count=1,
                    dead_code_score=0.1,
                ),
                Metric(
                    file_id=file_b.id,
                    cyclomatic=3,
                    cognitive=4,
                    lines_of_code=38,
                    function_count=2,
                    class_count=0,
                    dead_code_score=0.0,
                ),
                Symbol(
                    file_id=file_a.id,
                    name="orphan",
                    kind=SymbolKind.FUNCTION,
                    line_start=10,
                    line_end=20,
                    is_used=False,
                    usage_count=0,
                ),
                Symbol(
                    file_id=file_b.id,
                    name="hello",
                    kind=SymbolKind.FUNCTION,
                    line_start=1,
                    line_end=5,
                    is_used=True,
                    usage_count=3,
                ),
                Dependency(
                    from_file_id=file_a.id,
                    to_file_id=file_b.id,
                    kind=DependencyKind.IMPORT,
                    symbol="hello",
                    line=1,
                ),
            ]
        )
        # A succeeded job so SSE / latest endpoints have data.
        session.add(
            AnalysisJob(
                repository_id=repo.id,
                status=AnalysisJobStatus.SUCCEEDED,
                queued_at=datetime.now(UTC),
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                progress=100,
                progress_message="done",
            )
        )
        await session.commit()
        await session.refresh(repo)
        return repo


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@pytest.fixture
def repo_payload() -> dict[str, Any]:
    return {"url": "https://github.com/octocat/Hello-World", "branch": "main"}
