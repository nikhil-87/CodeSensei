"""Dead-code endpoint."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import DeadCodeServiceDep, verify_repository_access
from app.schemas.dead_code import DeadCodeReport

router = APIRouter(
    prefix="/repositories/{repository_id}",
    tags=["dead-code"],
    dependencies=[Depends(verify_repository_access)],
)


@router.get(
    "/dead-code",
    response_model=DeadCodeReport,
    summary="List unused symbols (functions, classes, exports)",
)
async def get_dead_code(
    repository_id: uuid.UUID,
    service: DeadCodeServiceDep,
) -> DeadCodeReport:
    return await service.report(repository_id)
