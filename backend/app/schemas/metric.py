"""Metric / complexity DTOs."""
from __future__ import annotations

import uuid

from pydantic import BaseModel


class FileComplexity(BaseModel):
    file_id: uuid.UUID
    path: str
    language: str
    cyclomatic: int
    cognitive: int
    lines_of_code: int
    function_count: int
    class_count: int


class ComplexityRanking(BaseModel):
    repository_id: uuid.UUID
    top_files: list[FileComplexity]
    average_cyclomatic: float
    average_cognitive: float
    median_lines_of_code: float
