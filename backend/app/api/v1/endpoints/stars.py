"""Star endpoints — GitHub-style starring + the viewer's starred list.

* ``PUT  /repositories/{id}/star`` — star (idempotent)
* ``DELETE /repositories/{id}/star`` — unstar (idempotent)
* ``GET  /me/stars`` — the authenticated user's starred repositories

Starring requires *read* access to the repository (owner or public); repos the
caller cannot see return 404 via ``RepositoryService.get_for_user`` — never
leaking their existence.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query

from app.core.dependencies import (
    CurrentUserDep,
    RepositoryServiceDep,
    StarServiceDep,
)
from app.schemas.common import PaginatedResponse
from app.schemas.repository import RepositoryRead
from app.schemas.star import StarState

router = APIRouter(tags=["stars"])


@router.put(
    "/repositories/{repository_id}/star",
    response_model=StarState,
    summary="Star a repository",
)
async def star_repository(
    repository_id: uuid.UUID,
    user: CurrentUserDep,
    repo_service: RepositoryServiceDep,
    star_service: StarServiceDep,
) -> StarState:
    repo = await repo_service.get_for_user(repository_id, user_id=user.id)
    count = await star_service.star(repo, user_id=user.id)
    return StarState(starred=True, star_count=count)


@router.delete(
    "/repositories/{repository_id}/star",
    response_model=StarState,
    summary="Remove a star from a repository",
)
async def unstar_repository(
    repository_id: uuid.UUID,
    user: CurrentUserDep,
    repo_service: RepositoryServiceDep,
    star_service: StarServiceDep,
) -> StarState:
    repo = await repo_service.get_for_user(repository_id, user_id=user.id)
    count = await star_service.unstar(repo, user_id=user.id)
    return StarState(starred=False, star_count=count)


@router.get(
    "/me/stars",
    response_model=PaginatedResponse[RepositoryRead],
    summary="List the repositories the authenticated user has starred",
)
async def list_my_stars(
    user: CurrentUserDep,
    repo_service: RepositoryServiceDep,
    star_service: StarServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> PaginatedResponse[RepositoryRead]:
    repos, total = await star_service.list_starred(
        user_id=user.id, page=page, page_size=page_size
    )
    # Every repo in this list is, by definition, starred by the viewer.
    items = repo_service.to_read_models_with_stars(
        repos, starred_ids={r.id for r in repos}
    )
    return PaginatedResponse[RepositoryRead](
        items=items, page=page, page_size=page_size, total=total
    )
