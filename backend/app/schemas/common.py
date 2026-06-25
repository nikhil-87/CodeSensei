"""Shared schemas used across multiple endpoints."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class ORMBase(BaseModel):
    """Base for read schemas that map from SQLAlchemy ORM objects."""

    model_config = ConfigDict(from_attributes=True, frozen=False)


class Pagination(BaseModel):
    """Cursor-less offset pagination — sufficient for our list sizes."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=200)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int


class HealthResponse(BaseModel):
    status: str = Field(default="ok", examples=["ok"])
    version: str
    checks: dict[str, str] = Field(default_factory=dict)
