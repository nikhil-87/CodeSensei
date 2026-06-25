"""Impact-analysis endpoint."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import ImpactServiceDep, verify_repository_access
from app.schemas.impact import ImpactAnalysisRequest, ImpactAnalysisResponse

router = APIRouter(
    prefix="/repositories/{repository_id}",
    tags=["impact"],
    dependencies=[Depends(verify_repository_access)],
)


@router.post(
    "/impact",
    response_model=ImpactAnalysisResponse,
    summary="Compute the blast-radius of changing a file",
)
async def analyze_impact(
    repository_id: uuid.UUID,
    payload: ImpactAnalysisRequest,
    service: ImpactServiceDep,
) -> ImpactAnalysisResponse:
    return await service.analyze(repository_id, payload)
