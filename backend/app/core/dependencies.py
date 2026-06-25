"""FastAPI dependency providers.

The DI container is just a set of callables here — FastAPI's `Depends` does
the rest. Provider functions are async where they touch I/O so the framework
can manage their lifetime.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import uuid

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_cache import RedisCache, get_redis_cache
from app.core.auth import decode_session_token
from app.core.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, RepositoryNotFoundError, UnauthorizedError
from app.db.session import get_session_factory
from app.models.user import User
from app.repositories.analysis_job_repository import AnalysisJobRepository
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.repositories.dependency_repository import DependencyRepository
from app.repositories.metric_repository import MetricRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.source_file_repository import SourceFileRepository
from app.repositories.star_repository import StarRepository
from app.repositories.symbol_repository import SymbolRepository
from app.repositories.user_repository import UserRepository
from app.services.analysis_service import AnalysisService
from app.services.architecture_service import ArchitectureService
from app.services.auth_service import AuthService
from app.services.chat_session_service import ChatSessionService
from app.services.dead_code_service import DeadCodeService
from app.services.dependency_service import DependencyService
from app.services.documentation_service import DocumentationService
from app.services.impact_service import ImpactService
from app.services.metric_service import MetricService
from app.services.profile_service import ProfileService
from app.services.repository_service import RepositoryService
from app.services.star_service import StarService
from app.services.ai_service import AIService
from app.workers.job_dispatcher import JobDispatcher


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
SettingsDep = Annotated[Settings, Depends(get_settings)]


# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------
async def get_db_session(settings: SettingsDep) -> AsyncIterator[AsyncSession]:
    factory = get_session_factory(settings)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------
async def get_cache(settings: SettingsDep) -> RedisCache:
    return get_redis_cache(settings)


CacheDep = Annotated[RedisCache, Depends(get_cache)]


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------
def _make_repository_repo(session: DbSessionDep) -> RepositoryRepository:
    return RepositoryRepository(session)


def _make_job_repo(session: DbSessionDep) -> AnalysisJobRepository:
    return AnalysisJobRepository(session)


def _make_source_file_repo(session: DbSessionDep) -> SourceFileRepository:
    return SourceFileRepository(session)


def _make_symbol_repo(session: DbSessionDep) -> SymbolRepository:
    return SymbolRepository(session)


def _make_dependency_repo(session: DbSessionDep) -> DependencyRepository:
    return DependencyRepository(session)


def _make_metric_repo(session: DbSessionDep) -> MetricRepository:
    return MetricRepository(session)


def _make_user_repo(session: DbSessionDep) -> UserRepository:
    return UserRepository(session)


def _make_chat_session_repo(session: DbSessionDep) -> ChatSessionRepository:
    return ChatSessionRepository(session)


def _make_chat_message_repo(session: DbSessionDep) -> ChatMessageRepository:
    return ChatMessageRepository(session)


def _make_star_repo(session: DbSessionDep) -> StarRepository:
    return StarRepository(session)


RepositoryRepoDep = Annotated[RepositoryRepository, Depends(_make_repository_repo)]
JobRepoDep = Annotated[AnalysisJobRepository, Depends(_make_job_repo)]
SourceFileRepoDep = Annotated[SourceFileRepository, Depends(_make_source_file_repo)]
SymbolRepoDep = Annotated[SymbolRepository, Depends(_make_symbol_repo)]
DependencyRepoDep = Annotated[DependencyRepository, Depends(_make_dependency_repo)]
MetricRepoDep = Annotated[MetricRepository, Depends(_make_metric_repo)]
UserRepoDep = Annotated[UserRepository, Depends(_make_user_repo)]
ChatSessionRepoDep = Annotated[ChatSessionRepository, Depends(_make_chat_session_repo)]
ChatMessageRepoDep = Annotated[ChatMessageRepository, Depends(_make_chat_message_repo)]
StarRepoDep = Annotated[StarRepository, Depends(_make_star_repo)]


# ---------------------------------------------------------------------------
# Job dispatcher
# ---------------------------------------------------------------------------
def _make_job_dispatcher(settings: SettingsDep) -> JobDispatcher:
    return JobDispatcher(settings)


JobDispatcherDep = Annotated[JobDispatcher, Depends(_make_job_dispatcher)]


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------
def _make_repository_service(
    repo_repo: RepositoryRepoDep,
    job_repo: JobRepoDep,
    dispatcher: JobDispatcherDep,
    settings: SettingsDep,
) -> RepositoryService:
    return RepositoryService(repo_repo, job_repo, dispatcher, settings)


def _make_analysis_service(
    repo_repo: RepositoryRepoDep,
    job_repo: JobRepoDep,
    dispatcher: JobDispatcherDep,
) -> AnalysisService:
    return AnalysisService(repo_repo, job_repo, dispatcher)


def _make_dependency_service(
    repo_repo: RepositoryRepoDep,
    file_repo: SourceFileRepoDep,
    dep_repo: DependencyRepoDep,
    cache: CacheDep,
) -> DependencyService:
    return DependencyService(repo_repo, file_repo, dep_repo, cache)


def _make_metric_service(
    repo_repo: RepositoryRepoDep,
    file_repo: SourceFileRepoDep,
    metric_repo: MetricRepoDep,
    cache: CacheDep,
) -> MetricService:
    return MetricService(repo_repo, file_repo, metric_repo, cache)


def _make_dead_code_service(
    repo_repo: RepositoryRepoDep,
    file_repo: SourceFileRepoDep,
    symbol_repo: SymbolRepoDep,
    cache: CacheDep,
) -> DeadCodeService:
    return DeadCodeService(repo_repo, file_repo, symbol_repo, cache)


def _make_impact_service(
    repo_repo: RepositoryRepoDep,
    file_repo: SourceFileRepoDep,
    dep_repo: DependencyRepoDep,
) -> ImpactService:
    return ImpactService(repo_repo, file_repo, dep_repo)


def _make_architecture_service(
    repo_repo: RepositoryRepoDep,
    file_repo: SourceFileRepoDep,
    dep_repo: DependencyRepoDep,
    cache: CacheDep,
) -> ArchitectureService:
    return ArchitectureService(repo_repo, file_repo, dep_repo, cache)


def _make_documentation_service(
    repo_repo: RepositoryRepoDep,
    file_repo: SourceFileRepoDep,
    dep_repo: DependencyRepoDep,
    metric_repo: MetricRepoDep,
) -> DocumentationService:
    return DocumentationService(repo_repo, file_repo, dep_repo, metric_repo)


def _make_ai_service(settings: SettingsDep) -> AIService:
    return AIService(settings)


def _make_chat_session_service(
    session_repo: ChatSessionRepoDep,
    message_repo: ChatMessageRepoDep,
    ai_service: "AIServiceDep",
    settings: SettingsDep,
) -> ChatSessionService:
    return ChatSessionService(session_repo, message_repo, ai_service, settings)


def _make_star_service(
    star_repo: StarRepoDep,
    repo_repo: RepositoryRepoDep,
) -> StarService:
    return StarService(star_repo, repo_repo)


def _make_profile_service(
    user_repo: UserRepoDep,
    repo_repo: RepositoryRepoDep,
) -> ProfileService:
    return ProfileService(user_repo, repo_repo)


RepositoryServiceDep = Annotated[RepositoryService, Depends(_make_repository_service)]
AnalysisServiceDep = Annotated[AnalysisService, Depends(_make_analysis_service)]
DependencyServiceDep = Annotated[DependencyService, Depends(_make_dependency_service)]
MetricServiceDep = Annotated[MetricService, Depends(_make_metric_service)]
DeadCodeServiceDep = Annotated[DeadCodeService, Depends(_make_dead_code_service)]
ImpactServiceDep = Annotated[ImpactService, Depends(_make_impact_service)]
ArchitectureServiceDep = Annotated[ArchitectureService, Depends(_make_architecture_service)]
DocumentationServiceDep = Annotated[DocumentationService, Depends(_make_documentation_service)]
AIServiceDep = Annotated[AIService, Depends(_make_ai_service)]
ChatSessionServiceDep = Annotated[
    ChatSessionService, Depends(_make_chat_session_service)
]
StarServiceDep = Annotated[StarService, Depends(_make_star_service)]
ProfileServiceDep = Annotated[ProfileService, Depends(_make_profile_service)]


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
def _make_auth_service(user_repo: UserRepoDep, settings: SettingsDep) -> AuthService:
    return AuthService(user_repo, settings)


AuthServiceDep = Annotated[AuthService, Depends(_make_auth_service)]


async def get_optional_user(
    request: Request,
    settings: SettingsDep,
    user_repo: UserRepoDep,
) -> User | None:
    """Resolve the signed-in user from the session cookie, or ``None``.

    Never raises — use this for endpoints that serve both authenticated and
    anonymous callers (e.g. public/shared repositories).

    When ``MOCK_AUTH`` is enabled (local dev / tests only — never in production,
    see ``Settings.mock_auth_enabled``) every request is transparently
    authenticated as a single predefined mock user, bypassing GitHub OAuth.
    """
    if settings.mock_auth_enabled:
        return await user_repo.upsert_from_github(
            github_id=settings.mock_auth_github_id,
            username=settings.mock_auth_username,
            display_name=settings.mock_auth_display_name,
            email=settings.mock_auth_email,
            avatar_url=settings.mock_auth_avatar_url,
        )

    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        return None
    claims = decode_session_token(settings, token)
    if not claims:
        return None
    sub = claims.get("sub")
    if not sub:
        return None
    try:
        user_id = uuid.UUID(str(sub))
    except (ValueError, TypeError):
        return None
    return await user_repo.get(user_id)


OptionalUserDep = Annotated["User | None", Depends(get_optional_user)]


async def get_current_user(user: OptionalUserDep) -> User:
    """Require an authenticated user; 401 otherwise."""
    if user is None:
        raise UnauthorizedError("Authentication required")
    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


async def verify_repository_access(
    repository_id: uuid.UUID,
    request: Request,
    user: OptionalUserDep,
    repo_repo: RepositoryRepoDep,
) -> None:
    """Router-level guard for ``/repositories/{repository_id}/*`` sub-resources.

    - Owners may do anything.
    - Public repositories are readable by anyone via safe (GET/HEAD) methods.
    - Everything else is hidden behind a 404 so we never leak which repository
      ids exist (avoids the classic IDOR enumeration channel).
    """
    repo = await repo_repo.get(repository_id)
    if repo is None:
        raise RepositoryNotFoundError(f"Repository {repository_id} not found")

    is_owner = user is not None and repo.owner_id is not None and repo.owner_id == user.id
    if is_owner:
        return

    safe_method = request.method in ("GET", "HEAD", "OPTIONS")
    if repo.is_public and safe_method:
        return

    # Authenticated non-owner trying to mutate someone else's repo → 403;
    # otherwise hide existence entirely with a 404.
    if user is not None and repo.is_public:
        raise ForbiddenError("You do not have write access to this repository")
    raise RepositoryNotFoundError(f"Repository {repository_id} not found")
