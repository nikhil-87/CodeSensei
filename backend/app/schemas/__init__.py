"""Pydantic schemas (DTOs) — API contract surface."""
from __future__ import annotations

from app.schemas.ai import ChatMessage, ChatRequest, ChatTokenEvent
from app.schemas.analysis import AnalysisJobRead, AnalysisProgressEvent
from app.schemas.architecture import ArchitectureReport, LayerInfo
from app.schemas.chat import (
    AttachedContext,
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSessionUpdate,
    SessionChatRequest,
)
from app.schemas.common import HealthResponse, PaginatedResponse, Pagination
from app.schemas.dead_code import DeadCodeItem, DeadCodeReport
from app.schemas.dependency import DependencyEdge, DependencyGraphResponse, GraphNode
from app.schemas.documentation import DocumentationRequest, DocumentationResponse
from app.schemas.impact import ImpactAnalysisRequest, ImpactAnalysisResponse, ImpactedFile
from app.schemas.metric import ComplexityRanking, FileComplexity
from app.schemas.profile import PublicProfileRead
from app.schemas.repository import (
    RepositoryCreate,
    RepositoryDetail,
    RepositoryFreshness,
    RepositoryRead,
    RepositorySort,
    RepositoryStats,
)
from app.schemas.star import StarState

__all__ = [
    # ai
    "ChatMessage",
    "ChatRequest",
    "ChatTokenEvent",
    # analysis
    "AnalysisJobRead",
    "AnalysisProgressEvent",
    # architecture
    "ArchitectureReport",
    "LayerInfo",
    # chat sessions
    "AttachedContext",
    "ChatMessageRead",
    "ChatSessionCreate",
    "ChatSessionRead",
    "ChatSessionUpdate",
    "SessionChatRequest",
    # common
    "HealthResponse",
    "PaginatedResponse",
    "Pagination",
    # dead code
    "DeadCodeItem",
    "DeadCodeReport",
    # dependency
    "DependencyEdge",
    "DependencyGraphResponse",
    "GraphNode",
    # documentation
    "DocumentationRequest",
    "DocumentationResponse",
    # impact
    "ImpactAnalysisRequest",
    "ImpactAnalysisResponse",
    "ImpactedFile",
    # metric
    "ComplexityRanking",
    "FileComplexity",
    # profile
    "PublicProfileRead",
    # repository
    "RepositoryCreate",
    "RepositoryDetail",
    "RepositoryFreshness",
    "RepositoryRead",
    "RepositorySort",
    "RepositoryStats",
    # star
    "StarState",
]
