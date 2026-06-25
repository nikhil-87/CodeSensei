"""Metric — per-file aggregated metrics produced by the analysis engine."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_file import SourceFile


class Metric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "metrics"
    __table_args__ = (
        Index("ix_metrics_cyclomatic", "cyclomatic"),
        Index("ix_metrics_dead_code_score", "dead_code_score"),
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_files.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    cyclomatic: Mapped[int] = mapped_column(default=0, nullable=False)
    cognitive: Mapped[int] = mapped_column(default=0, nullable=False)
    lines_of_code: Mapped[int] = mapped_column(default=0, nullable=False)
    function_count: Mapped[int] = mapped_column(default=0, nullable=False)
    class_count: Mapped[int] = mapped_column(default=0, nullable=False)

    # 0..1 — likelihood the file is unreachable from any entry point.
    dead_code_score: Mapped[float] = mapped_column(
        Numeric(precision=4, scale=3),
        default=0,
        nullable=False,
    )

    file: Mapped["SourceFile"] = relationship(back_populates="metric")
