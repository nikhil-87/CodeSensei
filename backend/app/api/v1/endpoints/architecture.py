"""Architecture-discovery endpoint."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import ArchitectureServiceDep, verify_repository_access
from app.schemas.architecture import ArchitectureReport

router = APIRouter(
    prefix="/repositories/{repository_id}",
    tags=["architecture"],
    dependencies=[Depends(verify_repository_access)],
)


@router.get(
    "/architecture",
    response_model=ArchitectureReport,
    summary="Discover layers, components, and produce a Mermaid diagram",
)
async def get_architecture(
    repository_id: uuid.UUID,
    service: ArchitectureServiceDep,
) -> ArchitectureReport:
    return await service.report(repository_id)
