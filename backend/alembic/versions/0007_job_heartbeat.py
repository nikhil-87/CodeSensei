"""Add analysis_jobs.heartbeat_at for the stuck-job reaper.

Revision ID: 0007_job_heartbeat
Revises: 0006_active_job_unique
Create Date: 2026-06-24 00:00:00.000000

The worker writes ``heartbeat_at`` as it makes progress. The backend reaper
fails any RUNNING job whose heartbeat has gone stale (worker crashed), which
also clears the active-job unique index so the repository can be re-analyzed.
Without this a crashed worker would leave a repo permanently stuck in
ANALYZING / RUNNING.

Idempotent (``ADD COLUMN IF NOT EXISTS``).
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "0007_job_heartbeat"
down_revision: str | None = "0006_active_job_unique"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "ALTER TABLE analysis_jobs "
            "ADD COLUMN IF NOT EXISTS heartbeat_at TIMESTAMPTZ;"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("ALTER TABLE analysis_jobs DROP COLUMN IF EXISTS heartbeat_at;")
    )
