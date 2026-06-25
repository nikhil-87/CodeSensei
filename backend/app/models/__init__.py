"""SQLAlchemy ORM models.

Import all models here so Alembic's autogenerate sees them via `Base.metadata`.
`register_models()` is a no-op function whose only purpose is to provide a
single side-effect-free import path for the env.py file.
"""
from __future__ import annotations

from app.models.analysis_job import AnalysisJob, AnalysisJobStatus  # noqa: F401
from app.models.chat_message import ChatMessage  # noqa: F401
from app.models.chat_session import ChatSession  # noqa: F401
from app.models.dependency import Dependency, DependencyKind  # noqa: F401
from app.models.metric import Metric  # noqa: F401
from app.models.repository import Repository, RepositoryStatus  # noqa: F401
from app.models.source_file import SourceFile  # noqa: F401
from app.models.star import Star  # noqa: F401
from app.models.symbol import Symbol, SymbolKind  # noqa: F401
from app.models.user import User  # noqa: F401


def register_models() -> None:
    """No-op import anchor for Alembic env.py."""
    return None


__all__ = [
    "AnalysisJob",
    "AnalysisJobStatus",
    "ChatMessage",
    "ChatSession",
    "Dependency",
    "DependencyKind",
    "Metric",
    "Repository",
    "RepositoryStatus",
    "SourceFile",
    "Star",
    "Symbol",
    "SymbolKind",
    "User",
    "register_models",
]
