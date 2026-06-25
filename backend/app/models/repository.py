"""Repository model — top-level entity per analyzed GitHub repository."""
from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.analysis_job import AnalysisJob
    from app.models.source_file import SourceFile
    from app.models.user import User


class RepositoryStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    ANALYZING = "analyzing"
    READY = "ready"
    FAILED = "failed"


class Repository(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "repositories"
    __table_args__ = (
        # Each user gets their own copy of a given repo URL + branch.
        UniqueConstraint(
            "owner_id", "url", "branch", name="uq_repositories_owner_id_url_branch"
        ),
    )

    # App account that owns this analysis. Nullable for legacy/orphaned rows
    # created before authentication existed.
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    # When true, anyone with the link can view this analysis read-only.
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    default_branch: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    owner: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    status: Mapped[RepositoryStatus] = mapped_column(
        SAEnum(
            RepositoryStatus,
            name="repository_status",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=RepositoryStatus.PENDING,
        index=True,
    )
    error_message: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    analyzed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Provenance + versioning of the *last successful* analysis. Nullable so
    # legacy rows analyzed before versioning was introduced read as NULL and
    # are surfaced to the user as "unknown / refresh recommended" rather than
    # being silently treated as current. See shared.config.analysis_version.
    commit_hash: Mapped[str | None] = mapped_column(String(40), nullable=True)
    analysis_version: Mapped[int | None] = mapped_column(nullable=True)
    pipeline_version: Mapped[int | None] = mapped_column(nullable=True)
    schema_version: Mapped[int | None] = mapped_column(nullable=True)
    # Embedding strategy signature ("provider:model") the AI index was built
    # with; lets us detect an incompatible vector index after a model swap.
    embedding_model: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Aggregated stats populated by the worker on completion (denormalized for fast list views).
    file_count: Mapped[int] = mapped_column(default=0, nullable=False)
    total_lines: Mapped[int] = mapped_column(default=0, nullable=False)
    languages: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Denormalized count of stars, kept in sync by StarService so the public
    # discovery hub can sort by popularity without a per-row COUNT(*) join.
    star_count: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False, index=True
    )

    # Relationships
    owner_user: Mapped["User | None"] = relationship(back_populates="repositories")
    jobs: Mapped[list["AnalysisJob"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    files: Mapped[list["SourceFile"]] = relationship(
        back_populates="repository",
        cascade="all, delete-orphan",
    )
