"""Add analysis provenance + versioning columns to repositories.

Revision ID: 0003_analysis_versioning
Revises: 0002_users_and_ownership
Create Date: 2026-06-20 00:00:00.000000

Adds the stamps that let us tell whether a stored analysis was produced by the
current pipeline:

* ``commit_hash``      — the analyzed git commit SHA (provenance).
* ``analysis_version`` — analysis output/logic version.
* ``pipeline_version`` — orchestration/cloning pipeline version.
* ``schema_version``   — persisted-shape version.
* ``embedding_model``  — embedding signature the AI index was built with.

All columns are nullable: rows analyzed before this revision keep NULL and are
surfaced to the user as "unknown / refresh recommended" rather than being
treated as current. Idempotent (``IF NOT EXISTS``) to match the project style.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "0003_analysis_versioning"
down_revision: str | None = "0002_users_and_ownership"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


_COLUMNS = (
    ("commit_hash", "VARCHAR(40)"),
    ("analysis_version", "INTEGER"),
    ("pipeline_version", "INTEGER"),
    ("schema_version", "INTEGER"),
    ("embedding_model", "VARCHAR(255)"),
)


def upgrade() -> None:
    conn = op.get_bind()
    for name, ddl_type in _COLUMNS:
        conn.execute(
            text(
                f"ALTER TABLE repositories ADD COLUMN IF NOT EXISTS {name} {ddl_type};"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()
    for name, _ddl_type in _COLUMNS:
        conn.execute(
            text(f"ALTER TABLE repositories DROP COLUMN IF EXISTS {name};")
        )
