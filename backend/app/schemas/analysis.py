"""AnalysisJob DTOs."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.analysis_job import AnalysisJobStatus
from app.schemas.common import ORMBase


class AnalysisJobRead(ORMBase):
    id: uuid.UUID
    repository_id: uuid.UUID
    status: AnalysisJobStatus
    rq_job_id: str | None
    error: str | None
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    progress: int
    progress_message: str | None


class AnalysisProgressEvent(BaseModel):
    """Schema for SSE messages on the analysis progress stream."""

    event: Literal["queued", "running", "progress", "succeeded", "failed"]
    repository_id: uuid.UUID
    job_id: uuid.UUID
    progress: int = Field(ge=0, le=100)
    message: str | None = None
    error: str | None = None
