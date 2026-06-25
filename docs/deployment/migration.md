# Migration Guides

Because the services are stateless and providers are env-selected, migrating environments
is mostly editing `.env` + moving data. This doc covers each path.

## What changes vs. what stays the same

| Always the same | Changes per environment |
| --- | --- |
| Application code (frontend/backend/worker/engine) | URLs (`FRONTEND_BASE_URL`, OAuth callback) |
| Database schema (Alembic) | Data hosts (`POSTGRES_*`, `REDIS_*`) |
| API contract | Provider keys (`GROQ_API_KEY`, `HUGGINGFACE_API_KEY`) |
| Compose topology (free-tier) | `APP_ENV`, `APP_CORS_ORIGINS`, secrets |

## General migration checklist
1. Provision the target (VM / Codespace / managed DB+Redis).
2. Copy `.env`, update URLs/keys/hosts.
3. Migrate **Postgres** data (the only durable state besides Chroma):
   ```bash
   pg_dump "$OLD_DSN" > dump.sql
   psql "$NEW_DSN" < dump.sql
   docker exec codesensei-backend alembic upgrade head   # ensure head=0007
   ```
4. **Redis**: no migration needed (transient queue + cache).
5. **ChromaDB**: either copy the `chroma-data` volume, or simpler — **re-analyze** repos to
   rebuild indexes (idempotent upsert by `chunk_id`).
6. Update the **GitHub OAuth app** callback/homepage URLs to the new domain.
7. Bring up services + verify (see [local.md](local.md) checklist).

## Codespaces → Oracle Cloud
| Step | Action |
| --- | --- |
| Compute | Provision the Oracle A1 VM ([oracle-cloud.md](oracle-cloud.md)) |
| Data | Move to managed Neon + Upstash (or migrate container volumes) |
| URLs | Real domain + TLS; update OAuth callback + `FRONTEND_BASE_URL` |
| Env | `APP_ENV=production`, real `APP_SECRET_KEY`, restrict `APP_CORS_ORIGINS` |
| Downtime | Near-zero: stand up new env, migrate DB, flip DNS |
| Rollback | Keep the Codespace until the VM is verified; DNS revert |

## Local → Oracle Cloud
Same as above; the main change is `APP_ENV=production` and managed data services.

## Local → Codespaces
Mostly just OAuth callback URLs (dynamic forwarded domains) — or use `MOCK_AUTH=true`. See
[codespaces.md](codespaces.md).

## Oracle Cloud → another VPS
Identical pattern — the deployment is "Docker Compose + nginx + Let's Encrypt", which runs
on any Linux VM. Move the `.env`, migrate Postgres, re-point DNS, re-issue TLS.

## Why this is cheap (interview-ready answer)
- **Stateless compute** → no per-instance data to migrate.
- **Env-driven providers** → no code edits to swap DB/Redis/LLM/embeddings/OAuth.
- **Managed data** (Neon/Upstash) → the durable state already lives outside the VM.
- **Idempotent indexing** → the vector store can be rebuilt rather than migrated.

Downtime is dominated by DNS propagation and a `pg_dump`/`pg_restore`, not by code work.
