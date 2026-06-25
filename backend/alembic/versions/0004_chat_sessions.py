"""Add chat_sessions + chat_messages tables (persistent AI conversations).

Revision ID: 0004_chat_sessions
Revises: 0003_analysis_versioning
Create Date: 2026-06-24 00:00:00.000000

Persistent, user-private AI chat. A session belongs to one user and one
repository; messages cascade-delete with their session, and sessions
cascade-delete with their user or repository.

Idempotent (``IF NOT EXISTS``) to match the project's migration style — on a
fresh DB ``0001`` builds everything from ``Base.metadata`` first, so this
revision converges rather than conflicts.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision: str = "0004_chat_sessions"
down_revision: str | None = "0003_analysis_versioning"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id UUID NOT NULL,
                user_id UUID NOT NULL,
                repository_id UUID NOT NULL,
                title VARCHAR(200) NOT NULL DEFAULT 'New chat',
                last_activity_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT pk_chat_sessions PRIMARY KEY (id),
                CONSTRAINT fk_chat_sessions_user_id_users
                    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                CONSTRAINT fk_chat_sessions_repository_id_repositories
                    FOREIGN KEY (repository_id) REFERENCES repositories (id)
                    ON DELETE CASCADE
            );
            """
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_id "
            "ON chat_sessions (user_id);"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_chat_sessions_repository_id "
            "ON chat_sessions (repository_id);"
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_chat_sessions_user_repo_activity "
            "ON chat_sessions (user_id, repository_id, last_activity_at);"
        )
    )

    conn.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS chat_messages (
                id UUID NOT NULL,
                session_id UUID NOT NULL,
                role VARCHAR(16) NOT NULL,
                content TEXT NOT NULL,
                citations JSONB,
                attached_context JSONB,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                CONSTRAINT pk_chat_messages PRIMARY KEY (id),
                CONSTRAINT fk_chat_messages_session_id_chat_sessions
                    FOREIGN KEY (session_id) REFERENCES chat_sessions (id)
                    ON DELETE CASCADE
            );
            """
        )
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_chat_messages_session_id "
            "ON chat_messages (session_id);"
        )
    )
    # Ordered history reads: "all messages for a session, oldest first".
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created "
            "ON chat_messages (session_id, created_at);"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DROP TABLE IF EXISTS chat_messages CASCADE;"))
    conn.execute(text("DROP TABLE IF EXISTS chat_sessions CASCADE;"))
