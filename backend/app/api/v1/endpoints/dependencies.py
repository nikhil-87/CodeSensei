"""Dependency-graph endpoint."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import DependencyServiceDep, verify_repository_access
from app.schemas.dependency import DependencyGraphResponse

router = APIRouter(
    prefix="/repositories/{repository_id}",
    tags=["dependencies"],
    dependencies=[Depends(verify_repository_access)],
)


@router.get(
    "/dependencies",
    response_model=DependencyGraphResponse,
    summary="Get the dependency graph for a repository",
)
async def get_dependency_graph(
    repository_id: uuid.UUID,
    service: DependencyServiceDep,
) -> DependencyGraphResponse:
    return await service.get_graph(repository_id)
