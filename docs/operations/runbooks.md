# Operational Runbooks

Step-by-step procedures for running and recovering the system. Commands assume the
free-tier compose from the repo root.

## Startup
```bash
docker compose -f docker/docker-compose.free-tier.yml --env-file .env up -d --build
docker exec codesensei-backend alembic upgrade head
docker ps --filter "name=codesensei" --format "{{.Names}} {{.Status}}"
curl -s http://localhost:8000/api/v1/healthz   # liveness
curl -s http://localhost:8000/api/v1/readyz    # checks Postgres + Redis
```
Healthy = all four containers `Up (healthy)` and `/readyz` 200.

## Graceful shutdown
```bash
docker compose -f docker/docker-compose.free-tier.yml --env-file .env down
# keep data volumes; add -v ONLY if you intend to wipe Postgres/Chroma data
```
The worker handles SIGTERM/SIGINT and finishes its burst before exiting.

## Restart one service (e.g. after a frontend change)
```bash
docker compose -f docker/docker-compose.free-tier.yml --env-file .env up -d --build frontend
```

## Repository analysis is stuck / failed
Symptoms: a repo sits in `ANALYZING`, or a job is `RUNNING` forever.
1. Inspect the job: `GET /repositories/{id}/jobs/latest` (status, progress, heartbeat, error).
2. Check worker logs: `docker compose ... logs --tail=200 worker`.
3. If the worker died, the **reaper** will fail the job after
   `ANALYSIS_RUNNING_HEARTBEAT_TIMEOUT_SECONDS` and flip the repo to `FAILED`; the user can
   re-analyze.
4. To recover immediately: restart the worker, then `POST /repositories/{id}/analyze`.

## Worker failures / crash loop
1. `docker compose ... logs --tail=200 worker`.
2. Common causes: bad Redis creds (`REDIS_TLS`/password), OOM on a large repo (lower
   `WORKER_CONCURRENCY` / raise RAM), or a provider outage during indexing (non-fatal —
   `IndexingDegraded` is logged, job still succeeds).
3. Restart: `docker compose ... up -d --build worker`.

## Database issues
- **Can't connect**: verify `POSTGRES_*` + `POSTGRES_SSLMODE` (Neon needs `require`);
  `/readyz` will be 503.
- **Migration drift**: `docker exec codesensei-backend alembic current` (expect `0007`);
  apply with `alembic upgrade head`.
- **Restore**: `psql "$DSN" < dump.sql` then `alembic upgrade head`.

## AI / chat issues
- **No answer / 400**: check `GROQ_API_KEY` and `GROQ_CHAT_MODEL` (deprecated model →
  update). Free-tier rate limit (~30/min) can throttle.
- **Answers ignore the repo**: the repo may not be indexed (indexing degraded) → re-analyze;
  confirm `EMBEDDING_PROVIDER` + key.
- **Embedding mismatch after provider change**: re-analyze affected repos.

## ChromaDB issues
- Must be on **port 8000**; `/api/v1/heartbeat` should respond.
- Lost index → re-analyze repo (rebuilds vectors).
- Privacy cleanup: deleting a repo drops its collection automatically.

## Deployment failures
- **Site unreachable (Oracle)**: check OCI security list **and** host iptables for 80/443.
- **OAuth mismatch**: callback URL must equal `GITHUB_OAUTH_CALLBACK_URL`.
- **CORS errors**: `APP_CORS_ORIGINS` must include the frontend origin.
- **New code not live**: rebuild the specific service image and hard-refresh the browser
  (hashed bundle changes).

## Recovery summary
| Failure | Automatic recovery | Manual step |
| --- | --- | --- |
| Worker dies mid-job | reaper → job/repo FAILED | restart worker, re-analyze |
| Indexing degraded | job still SUCCEEDS | re-analyze when provider back |
| Duplicate analyze | `409` | none |
| DB down | `/readyz` 503 | restore connectivity, re-run migrations |
| Bad model name | chat 400 | update `GROQ_CHAT_MODEL` |
