"""Impact-analysis DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ImpactAnalysisRequest(BaseModel):
    file_path: str = Field(min_length=1, max_length=1024)
    max_depth: int = Field(default=5, ge=1, le=20)


class ImpactedFile(BaseModel):
    file_id: uuid.UUID
    path: str
    distance: int
    risk_score: float = Field(ge=0.0, le=1.0)


class ImpactAnalysisResponse(BaseModel):
    repository_id: uuid.UUID
    source_file: str
    impacted_files: list[ImpactedFile]
    risk_score: float = Field(ge=0.0, le=1.0)
    summary: str
