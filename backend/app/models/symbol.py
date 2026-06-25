"""Symbol — a named declaration (function / class / method / variable) in a file."""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.source_file import SourceFile


class SymbolKind(str, enum.Enum):
    FUNCTION = "function"
    METHOD = "method"
    CLASS = "class"
    INTERFACE = "interface"
    STRUCT = "struct"
    ENUM = "enum"
    VARIABLE = "variable"
    CONSTANT = "constant"
    TYPE_ALIAS = "type_alias"
    MODULE = "module"


class Symbol(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "symbols"
    __table_args__ = (
        Index("ix_symbols_file_kind", "file_id", "kind"),
        Index("ix_symbols_name", "name"),
    )

    file_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("source_files.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(512), nullable=False)
    qualified_name: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    kind: Mapped[SymbolKind] = mapped_column(
        SAEnum(
            SymbolKind,
            name="symbol_kind",
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
    )
    line_start: Mapped[int] = mapped_column(default=0, nullable=False)
    line_end: Mapped[int] = mapped_column(default=0, nullable=False)

    is_exported: Mapped[bool] = mapped_column(default=False, nullable=False)
    is_used: Mapped[bool] = mapped_column(default=True, nullable=False, index=True)
    usage_count: Mapped[int] = mapped_column(default=0, nullable=False)

    file: Mapped["SourceFile"] = relationship(back_populates="symbols")
