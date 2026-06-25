"""Public profile endpoints — ``/users/{username}`` and their public repos.

Read-only and anonymous-friendly. Only public-safe profile fields and a user's
public, analyzed repositories are exposed. An unknown handle is a 404.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import (
    OptionalUserDep,
    ProfileServiceDep,
    RepositoryServiceDep,
    StarServiceDep,
)
from app.schemas.common import PaginatedResponse
from app.schemas.profile import PublicProfileRead
from app.schemas.repository import RepositoryRead, RepositorySort

router = APIRouter(prefix="/users", tags=["profiles"])


@router.get(
    "/{username}",
    response_model=PublicProfileRead,
    summary="Get a user's public profile",
)
async def get_profile(
    username: str,
    profile_service: ProfileServiceDep,
) -> PublicProfileRead:
    return await profile_service.get_profile(username)


@router.get(
    "/{username}/repositories",
    response_model=PaginatedResponse[RepositoryRead],
    summary="List a user's public, analyzed repositories",
)
async def get_profile_repositories(
    username: str,
    user: OptionalUserDep,
    profile_service: ProfileServiceDep,
    repo_service: RepositoryServiceDep,
    star_service: StarServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    sort: RepositorySort = Query(default="stars"),
) -> PaginatedResponse[RepositoryRead]:
    repos, total = await profile_service.list_public_repositories(
        username, page=page, page_size=page_size, sort=sort
    )
    starred_ids = (
        await star_service.starred_ids(
            user_id=user.id, repository_ids=[r.id for r in repos]
        )
        if user is not None
        else set()
    )
    items = repo_service.to_read_models_with_stars(repos, starred_ids=starred_ids)
    return PaginatedResponse[RepositoryRead](
        items=items, page=page, page_size=page_size, total=total
    )
