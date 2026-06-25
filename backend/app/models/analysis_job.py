"""AnalysisJob — one row per worker invocation against a repository."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class AnalysisJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AnalysisJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "analysis_jobs"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[AnalysisJobStatus] = mapped_column(
        SAEnum(
            AnalysisJobStatus,
            name="analysis_job_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=AnalysisJobStatus.QUEUED,
        index=True,
    )
    rq_job_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    error: Mapped[str | None] = mapped_column(String(4096), nullable=True)

    queued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Liveness signal written by the worker as it makes progress. A RUNNING job
    # whose heartbeat goes stale is presumed dead (worker crashed) and reaped.
    heartbeat_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Progress reporting (0..100). The worker writes incremental updates here
    # which the SSE endpoint streams to the frontend.
    progress: Mapped[int] = mapped_column(default=0, nullable=False)
    progress_message: Mapped[str | None] = mapped_column(String(512), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="jobs")
