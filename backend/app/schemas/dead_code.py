"""Dead-code DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.symbol import SymbolKind


class DeadCodeItem(BaseModel):
    file_id: uuid.UUID
    path: str
    symbol_name: str
    kind: SymbolKind
    line_start: int
    line_end: int
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class DeadCodeReport(BaseModel):
    repository_id: uuid.UUID
    items: list[DeadCodeItem]
    summary: dict[str, int]
