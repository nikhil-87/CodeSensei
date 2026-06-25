"""Add stars table + repositories.star_count (social: stars & discovery).

Revision ID: 0005_social
Revises: 0004_chat_sessions
Create Date: 2026-06-24 00:00:00.000000

Introduces GitHub-style stars. A star is a unique (user, repository) join row;
``repositories.star_count`` is a denormalized counter kept in sync by the
service layer so the public discovery hub can sort by popularity cheaply.

Idempotent (``IF NOT EXISTS`` / guarded ``ADD COLUMN``) to match the project's
migration style — on a fresh DB ``0001`` builds everything from
``Base.metadata`` first, so this revision converges rather than conflicts.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "0005_social"
down_revision: str | None = "0004_chat_sessions"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Denormalized star counter on repositories.
    conn.execute(
        text(
            "ALTER TABLE repositories "
            "ADD COLUMN IF NOT EXISTS star_count INTEGER NOT NULL DEFAULT 0;"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_repositories_star_count "
            "ON repositories (star_count);"
        )
    )

    # Stars join table.
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS stars (
                id UUID NOT NULL,
                user_id UUID NOT NULL,
                repository_id UUID NOT NULL,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT pk_stars PRIMARY KEY (id),
                CONSTRAINT uq_stars_user_repository UNIQUE (user_id, repository_id),
                CONSTRAINT fk_stars_user_id_users
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                CONSTRAINT fk_stars_repository_id_repositories
                    FOREIGN KEY (repository_id) REFERENCES repositories (id)
                    ON DELETE CASCADE
            );
            """
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_stars_user_id ON stars (user_id);")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_stars_repository_id "
            "ON stars (repository_id);"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS stars CASCADE;"))
    conn.execute(text("DROP INDEX IF EXISTS ix_repositories_star_count;"))
    conn.execute(text("ALTER TABLE repositories DROP COLUMN IF EXISTS star_count;"))
