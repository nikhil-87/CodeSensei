"""Initial schema - generated from the SQLAlchemy models.

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-14 00:00:00.000000

The schema is created directly from ``Base.metadata`` so it can never drift
from the ORM models. ``upgrade`` first drops any pre-existing tables/enum
types (idempotent) and then recreates everything to match the models.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

from app.db.base import Base
from app.models import register_models

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_TABLES = (
    "dependencies",
    "metrics",
    "symbols",
    "source_files",
    "analysis_jobs",
    "repositories",
)

_ENUMS = (
    "dependency_kind",
    "symbol_kind",
    "analysis_job_status",
    "repository_status",
)


def upgrade() -> None:
    """Create the full schema from the ORM models.

    Drops any drifted tables/enum types first so the migration is safe to
    re-run against a database created by an older revision of the models.
    """
    register_models()  # ensure every model is imported into Base.metadata
    conn = op.get_bind()

    for table in _TABLES:
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
    for enum_name in _ENUMS:
        conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE;"))

    Base.metadata.create_all(bind=conn)


def downgrade() -> None:
    """Drop all tables and enum types."""
    conn = op.get_bind()
    for table in _TABLES:
        conn.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE;"))
    for enum_name in _ENUMS:
        conn.execute(text(f"DROP TYPE IF EXISTS {enum_name} CASCADE;"))
