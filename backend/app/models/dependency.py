"""Dependency — directed edge between two source files."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_file import SourceFile


class DependencyKind(str, enum.Enum):
    IMPORT = "import"
    INHERITANCE = "inheritance"
    CALL = "call"
    INSTANTIATION = "instantiation"
    REFERENCE = "reference"


class Dependency(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "dependencies"
    __table_args__ = (
        UniqueConstraint(
            "from_file_id", "to_file_id", "kind", "symbol",
            name="uq_dependencies_edge",
        ),
        Index("ix_dependencies_from", "from_file_id"),
        Index("ix_dependencies_to", "to_file_id"),
    )

    from_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_files.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_files.id", ondelete="CASCADE"),
        nullable=False,
    )

    kind: Mapped[DependencyKind] = mapped_column(
        SAEnum(
            DependencyKind,
            name="dependency_kind",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    symbol: Mapped[str | None] = mapped_column(String(512), nullable=True)
    line: Mapped[int | None] = mapped_column(nullable=True)

    from_file: Mapped["SourceFile"] = relationship(
        back_populates="outgoing_deps",
        foreign_keys=[from_file_id],
    )
    to_file: Mapped["SourceFile"] = relationship(
        back_populates="incoming_deps",
        foreign_keys=[to_file_id],
    )
