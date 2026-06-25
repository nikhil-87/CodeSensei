# ============================================================================
# Postgres bootstrap — runs *only* when the data volume is empty.
# The POSTGRES_DB / POSTGRES_USER / POSTGRES_PASSWORD env vars from compose
# are already applied by the entrypoint; this script just adds extras.
# ============================================================================

-- Trigram index support for the future search endpoints.
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Useful for cleaning out abandoned analysis jobs in cron later.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Per-application schema separation. Alembic owns ``public``, but we
-- carve out ``ops`` for read-only diagnostic views the platform team uses.
CREATE SCHEMA IF NOT EXISTS ops AUTHORIZATION CURRENT_USER;

COMMENT ON SCHEMA ops IS
    'Operational reporting views. Owned by the platform user; do not migrate.';
