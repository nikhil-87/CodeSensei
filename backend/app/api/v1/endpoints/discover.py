"""Discovery hub — browse public, analyzed repositories (repository-centric).

A repository (``url`` + ``branch``) may have multiple public analyses by
different users; Discover lists the *repository* once and a dedicated overview
lists each public analysis. Anonymous-friendly: an :class:`OptionalUser` lets us
flag ``viewer_has_starred`` for signed-in callers while serving everyone.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import (
    OptionalUserDep,
    RepositoryServiceDep,
    StarServiceDep,
)
from app.schemas.common import PaginatedResponse
from app.schemas.discover import DiscoverRepositoryRead, RepositoryGroupDetail
from app.schemas.repository import RepositorySort

router = APIRouter(prefix="/discover", tags=["discover"])


@router.get(
    "/repositories",
    response_model=PaginatedResponse[DiscoverRepositoryRead],
    summary="Browse public repositories (one card per repository)",
)
async def discover_repositories(
    repo_service: RepositoryServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=24, ge=1, le=100),
    sort: RepositorySort = Query(default="stars"),
    q: str | None = Query(default=None, max_length=200),
    language: str | None = Query(default=None, max_length=64),
) -> PaginatedResponse[DiscoverRepositoryRead]:
    query = q.strip() if q and q.strip() else None
    lang = language.strip() if language and language.strip() else None
    items, total = await repo_service.list_public_grouped(
        page=page, page_size=page_size, sort=sort, query=query, language=lang
    )
    return PaginatedResponse[DiscoverRepositoryRead](
        items=items, page=page, page_size=page_size, total=total
    )


@router.get(
    "/repository",
    response_model=RepositoryGroupDetail,
    summary="A repository's public analyses (the overview / history page)",
)
async def discover_repository(
    user: OptionalUserDep,
    repo_service: RepositoryServiceDep,
    star_service: StarServiceDep,
    url: str = Query(..., max_length=2048),
    branch: str | None = Query(default=None, max_length=255),
) -> RepositoryGroupDetail:
    # Load the group, then (for signed-in callers) annotate which analyses the
    # viewer has starred.
    group = await repo_service.public_repository_group(
        url=url, branch=branch, starred_ids=set()
    )
    if user is not None:
        starred = await star_service.starred_ids(
            user_id=user.id,
            repository_ids=[a.repository_id for a in group.analyses],
        )
        for analysis in group.analyses:
            analysis.viewer_has_starred = analysis.repository_id in starred
    return group

