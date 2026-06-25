"""Complexity-ranking endpoint."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import MetricServiceDep, verify_repository_access
from app.schemas.metric import ComplexityRanking

router = APIRouter(
    prefix="/repositories/{repository_id}",
    tags=["complexity"],
    dependencies=[Depends(verify_repository_access)],
)


@router.get(
    "/complexity",
    response_model=ComplexityRanking,
    summary="Rank files by cyclomatic / cognitive complexity",
)
async def get_complexity(
    repository_id: uuid.UUID,
    service: MetricServiceDep,
    top_n: int = Query(default=10, ge=1, le=100),
) -> ComplexityRanking:
    return await service.complexity_ranking(repository_id, top_n=top_n)
