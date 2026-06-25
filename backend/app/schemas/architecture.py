"""Architecture-discovery DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class LayerInfo(BaseModel):
    name: str
    file_count: int
    files: list[str]


class ArchitectureReport(BaseModel):
    repository_id: uuid.UUID
    layers: list[LayerInfo]
    components: list[LayerInfo]
    mermaid_diagram: str
    summary: str
