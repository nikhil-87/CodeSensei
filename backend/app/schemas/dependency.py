"""Dependency-graph DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.models.dependency import DependencyKind


class GraphNode(BaseModel):
    id: uuid.UUID
    path: str
    language: str
    line_count: int
    in_degree: int = 0
    out_degree: int = 0


class DependencyEdge(BaseModel):
    from_id: uuid.UUID = Field(alias="from")
    to_id: uuid.UUID = Field(alias="to")
    kind: DependencyKind
    symbol: str | None = None

    model_config = {"populate_by_name": True}


class DependencyGraphResponse(BaseModel):
    repository_id: uuid.UUID
    nodes: list[GraphNode]
    edges: list[DependencyEdge]
    cycles: list[list[uuid.UUID]] = Field(default_factory=list)
