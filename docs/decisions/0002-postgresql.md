# ADR-0002: PostgreSQL as the system of record

**Status:** Accepted

## Context
Analysis produces highly relational data — repositories own files, files declare symbols
and metrics, files depend on files. We also need uniqueness guarantees (one active job per
repo, one star per user/repo), flexible message metadata (citations), and a free managed
option.

## Decision
Use **PostgreSQL** as the single relational system of record, with Alembic migrations and
SQLAlchemy 2.0 async ORM. Use **JSONB** for semi-structured message metadata and **partial
unique indexes** for invariants.

## Alternatives considered
- **MySQL** — viable, but weaker partial-index / JSONB ergonomics.
- **MongoDB / document store** — poor fit for the heavily relational graph (files↔symbols↔
  deps) and cross-entity joins.
- **SQLite** — fine for dev, not for concurrent workers + API in production.

## Consequences
- (+) Relational integrity with cascade deletes models the domain cleanly.
- (+) Partial unique index enforces "one active job per repo" in the DB, not just app code.
- (+) JSONB stores citations/attached-context without extra tables.
- (+) Free managed tier (Neon) for cloud.
- (−) Vector search is not its job → a separate vector store (ChromaDB) is needed.
- (−) Async SQLAlchemy session management requires discipline.
