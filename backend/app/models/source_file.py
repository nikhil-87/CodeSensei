"""SourceFile — a single file inside an analyzed repository."""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.dependency import Dependency
    from app.models.metric import Metric
    from app.models.repository import Repository
    from app.models.symbol import Symbol


class SourceFile(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "source_files"
    __table_args__ = (
        UniqueConstraint("repository_id", "path", name="uq_source_files_repo_path"),
        Index("ix_source_files_language", "language"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    language: Mapped[str] = mapped_column(String(32), nullable=False)
    line_count: Mapped[int] = mapped_column(default=0, nullable=False)
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    repository: Mapped["Repository"] = relationship(back_populates="files")
    symbols: Mapped[list["Symbol"]] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
    )
    metric: Mapped["Metric | None"] = relationship(
        back_populates="file",
        cascade="all, delete-orphan",
        uselist=False,
    )
    outgoing_deps: Mapped[list["Dependency"]] = relationship(
        back_populates="from_file",
        foreign_keys="Dependency.from_file_id",
        cascade="all, delete-orphan",
    )
    incoming_deps: Mapped[list["Dependency"]] = relationship(
        back_populates="to_file",
        foreign_keys="Dependency.to_file_id",
    )
