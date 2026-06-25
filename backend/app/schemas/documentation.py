"""Documentation-generator DTOs."""
from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, Field

DocumentKind = Literal[
    "readme",
    "architecture",
    "api",
    "onboarding",
    "technical_design",
    "summary",
]


class DocumentationRequest(BaseModel):
    kind: DocumentKind = Field(description="Type of document to generate.")


class DocumentationResponse(BaseModel):
    repository_id: uuid.UUID
    kind: DocumentKind
    content_markdown: str
    generated_at: str
