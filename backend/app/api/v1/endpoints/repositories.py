"""Repository endpoints — CRUD over analyzed repositories."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Response, status
from pydantic import BaseModel

from app.core.dependencies import (
    AIServiceDep,
    CurrentUserDep,
    OptionalUserDep,
    RepositoryServiceDep,
    StarServiceDep,
)
from app.models.repository import RepositoryStatus
from app.observability.metrics import analysis_jobs_enqueued_total
from app.schemas.analysis import AnalysisJobRead
from app.schemas.common import PaginatedResponse
from app.schemas.repository import RepositoryCreate, RepositoryRead

router = APIRouter(prefix="/repositories", tags=["repositories"])


class VisibilityUpdate(BaseModel):
    is_public: bool


@router.post(
    "",
    response_model=AnalysisJobRead,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a GitHub repository for analysis",
)
async def submit_repository(
    payload: RepositoryCreate,
    service: RepositoryServiceDep,
    user: CurrentUserDep,
) -> AnalysisJobRead:
    _repo, job = await service.submit(payload, owner_id=user.id)
    analysis_jobs_enqueued_total.inc()
    return AnalysisJobRead.model_validate(job)


@router.get(
    "",
    response_model=PaginatedResponse[RepositoryRead],
    summary="List the authenticated user's repositories",
)
async def list_repositories(
    service: RepositoryServiceDep,
    user: CurrentUserDep,
    star_service: StarServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    repo_status: RepositoryStatus | None = Query(default=None, alias="status"),
) -> PaginatedResponse[RepositoryRead]:
    items, total = await service.list(
        page=page,
        page_size=page_size,
        status=repo_status,
        owner_id=user.id,
    )
    starred_ids = await star_service.starred_ids(
        user_id=user.id, repository_ids=[i.id for i in items]
    )
    return PaginatedResponse[RepositoryRead](
        items=service.to_read_models_with_stars(items, starred_ids=starred_ids),
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get(
    "/{repository_id}",
    response_model=RepositoryRead,
    summary="Fetch a single repository (owner or public)",
)
async def get_repository(
    repository_id: uuid.UUID,
    service: RepositoryServiceDep,
    user: OptionalUserDep,
    star_service: StarServiceDep,
) -> RepositoryRead:
    repo = await service.get_for_user(
        repository_id, user_id=user.id if user else None
    )
    model = service.to_read_model(repo)
    if user is not None:
        model.viewer_has_starred = await star_service.is_starred(
            user_id=user.id, repository_id=repo.id
        )
    return model


@router.patch(
    "/{repository_id}/visibility",
    response_model=RepositoryRead,
    summary="Toggle whether a repository is publicly shareable",
)
async def update_repository_visibility(
    repository_id: uuid.UUID,
    payload: VisibilityUpdate,
    service: RepositoryServiceDep,
    user: CurrentUserDep,
) -> RepositoryRead:
    repo = await service.set_visibility(
        repository_id, owner_id=user.id, is_public=payload.is_public
    )
    return service.to_read_model(repo)


@router.delete(
    "/{repository_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a repository and all its analysis data",
)
async def delete_repository(
    repository_id: uuid.UUID,
    service: RepositoryServiceDep,
    ai_service: AIServiceDep,
    user: CurrentUserDep,
) -> Response:
    await service.delete(repository_id, owner_id=user.id)
    # Purge the vector index too — the Postgres cascade doesn't reach ChromaDB,
    # and a deleted private repo's code chunks must not linger there.
    ai_service.delete_repository_index(repository_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
