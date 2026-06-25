# Database Documentation

PostgreSQL is the system of record. Start here.

| Doc | Covers |
| --- | --- |
| [schema.md](schema.md) | All 11 tables: columns, types, constraints, indexes, ERD, rationale |
| [migrations.md](migrations.md) | Alembic history (head `0007`), commands, conventions |
| [data-lifecycle.md](data-lifecycle.md) | Create/update/delete per entity, hot queries, caching, isolation |

ORM source: `backend/app/models/`. Migrations: `backend/alembic/versions/`.
