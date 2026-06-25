"""Prevent duplicate concurrent analysis jobs per repository.

Revision ID: 0006_active_job_unique
Revises: 0005_social
Create Date: 2026-06-24 00:00:00.000000

``AnalysisService.trigger`` / ``RepositoryService.submit`` check
``has_active_job`` then insert a new job — a classic check-then-act race. Two
requests that arrive together both pass the check and enqueue *duplicate*
expensive analyses. This partial unique index makes the database the single
arbiter: at most one QUEUED/RUNNING job may exist per repository, so the second
concurrent insert fails with an IntegrityError the service maps to
``analysis_already_running`` (409).

Idempotent and self-healing: before creating the index we cancel any pre-existing
duplicate active jobs (keeping the most recent), so the unique constraint can be
applied to dirty data without erroring.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "0006_active_job_unique"
down_revision: str | None = "0005_social"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Resolve any existing duplicates first: keep the newest active job per repo,
    # cancel the rest, so the partial unique index can be created cleanly.
    conn.execute(
        text(
            """
            UPDATE analysis_jobs aj
            SET status = 'cancelled',
                completed_at = COALESCE(aj.completed_at, now())
            WHERE aj.status IN ('queued', 'running')
              AND aj.id <> (
                  SELECT inner_aj.id
                  FROM analysis_jobs inner_aj
                  WHERE inner_aj.repository_id = aj.repository_id
                    AND inner_aj.status IN ('queued', 'running')
                  ORDER BY inner_aj.queued_at DESC, inner_aj.id DESC
                  LIMIT 1
              );
            """
        )
    )

    conn.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_active_job_per_repository "
            "ON analysis_jobs (repository_id) "
            "WHERE status IN ('queued', 'running');"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP INDEX IF EXISTS uq_active_job_per_repository;"))
