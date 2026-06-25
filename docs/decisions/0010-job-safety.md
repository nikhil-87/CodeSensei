# ADR-0010: Unique active-job index + heartbeat reaper

**Status:** Accepted

## Context
RQ gives at-least-once delivery and workers can crash mid-job. Two risks follow: (1) the
same repo could be analyzed twice concurrently (wasted work, race on persistence), and (2) a
crashed worker could leave a job `RUNNING` and a repo `ANALYZING` forever.

## Decision
Two complementary mechanisms:
1. **Partial unique index** `uq_active_job_per_repository(repository_id, status) WHERE status
   IN ('queued','running')` — the database forbids a second active job per repo; a duplicate
   enqueue surfaces as `409`.
2. **Heartbeat + reaper** — the worker writes `analysis_jobs.heartbeat_at` on every progress
   update; a background `analysis_reaper` loop (in the API lifespan) fails jobs whose
   heartbeat is stale (or that sat `QUEUED` too long) and flips their repos to `FAILED`.

## Alternatives considered
- **App-level locking only** — racy across replicas; the DB constraint is authoritative.
- **RQ's own job registry / TTLs** — helps, but doesn't model "repo is busy" or recover the
  repo's status; the reaper owns domain recovery.

## Consequences
- (+) "One analysis per repo" is guaranteed at the database level.
- (+) Crashes self-heal: stuck jobs become `FAILED` and the user can retry.
- (+) An immediate startup sweep clears orphans left by a crash.
- (−) Two timeouts to tune (`ANALYSIS_RUNNING_HEARTBEAT_TIMEOUT_SECONDS`,
  `ANALYSIS_QUEUED_TIMEOUT_SECONDS`); too low → false reaps, too high → slow recovery.
See [../features/repository-analysis.md](../features/repository-analysis.md).
