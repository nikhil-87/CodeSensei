"""Add users table + repository ownership and visibility.

Revision ID: 0002_users_and_ownership
Revises: 0001_initial
Create Date: 2026-06-19 00:00:00.000000

Idempotent on purpose: the project's ``0001_initial`` migration builds the
whole schema from ``Base.metadata`` (``create_all``), so on a *fresh* database
the new ``users`` table and ``repositories`` columns already exist by the time
this revision runs. On an *existing* database (already migrated to 0001 before
auth existed) this revision adds the delta. Every statement is guarded with
``IF [NOT] EXISTS`` so both paths converge on the same final schema.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "0002_users_and_ownership"
down_revision: str | None = "0001_initial"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # 1. users table -------------------------------------------------------
    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS users (
                id UUID NOT NULL,
                github_id BIGINT NOT NULL,
                username VARCHAR(255) NOT NULL,
                display_name VARCHAR(255),
                email VARCHAR(320),
                avatar_url VARCHAR(1024),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT pk_users PRIMARY KEY (id)
            );
            """
        )
    )
    # PRIMARY KEY already declared above on fresh creates; guard the rest.
    conn.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_github_id "
            "ON users (github_id);"
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);")
    )

    # 2. repositories.owner_id + is_public --------------------------------
    conn.execute(
        text("ALTER TABLE repositories ADD COLUMN IF NOT EXISTS owner_id UUID;")
    )
    conn.execute(
        text(
            "ALTER TABLE repositories ADD COLUMN IF NOT EXISTS is_public "
            "BOOLEAN NOT NULL DEFAULT false;"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_repositories_owner_id "
            "ON repositories (owner_id);"
        )
    )
    # FK repositories.owner_id -> users.id (guarded — Postgres lacks
    # ADD CONSTRAINT IF NOT EXISTS, so check the catalog first).
    conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'fk_repositories_owner_id_users'
                ) THEN
                    ALTER TABLE repositories
                        ADD CONSTRAINT fk_repositories_owner_id_users
                        FOREIGN KEY (owner_id) REFERENCES users (id)
                        ON DELETE CASCADE;
                END IF;
            END $$;
            """
        )
    )

    # 3. Swap the uniqueness scope from (url, branch) to (owner_id, url, branch)
    conn.execute(
        text(
            "ALTER TABLE repositories "
            "DROP CONSTRAINT IF EXISTS uq_repositories_url_branch;"
        )
    )
    conn.execute(
        text(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_repositories_owner_id_url_branch'
                ) THEN
                    ALTER TABLE repositories
                        ADD CONSTRAINT uq_repositories_owner_id_url_branch
                        UNIQUE (owner_id, url, branch);
                END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "ALTER TABLE repositories "
            "DROP CONSTRAINT IF EXISTS uq_repositories_owner_id_url_branch;"
        )
    )
    conn.execute(
        text(
            "ALTER TABLE repositories "
            "DROP CONSTRAINT IF EXISTS fk_repositories_owner_id_users;"
        )
    )
    conn.execute(text("DROP INDEX IF EXISTS ix_repositories_owner_id;"))
    conn.execute(
        text("ALTER TABLE repositories DROP COLUMN IF EXISTS is_public;")
    )
    conn.execute(
        text("ALTER TABLE repositories DROP COLUMN IF EXISTS owner_id;")
    )
    conn.execute(
        text(
            "ALTER TABLE repositories "
            "ADD CONSTRAINT uq_repositories_url_branch UNIQUE (url, branch);"
        )
    )
    conn.execute(text("DROP TABLE IF EXISTS users CASCADE;"))
