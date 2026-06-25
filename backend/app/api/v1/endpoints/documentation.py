"""Documentation-generation endpoint."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends

from app.core.dependencies import DocumentationServiceDep, verify_repository_access
from app.schemas.documentation import DocumentationRequest, DocumentationResponse

router = APIRouter(
    prefix="/repositories/{repository_id}",
    tags=["documentation"],
    dependencies=[Depends(verify_repository_access)],
)


@router.post(
    "/documentation",
    response_model=DocumentationResponse,
    summary="Generate README / architecture / onboarding / API documentation",
)
async def generate_documentation(
    repository_id: uuid.UUID,
    payload: DocumentationRequest,
    service: DocumentationServiceDep,
) -> DocumentationResponse:
    return await service.generate(repository_id, payload)
