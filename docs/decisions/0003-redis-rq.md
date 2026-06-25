# ADR-0003: Redis + RQ for background jobs

**Status:** Accepted

## Context
Repository analysis is slow (clone + parse + persist + embed) and must run off the request
path. We need a simple, free-tier-friendly job queue, plus a cache for analysis read-models.

## Decision
Use **Redis** as both the job broker (via **RQ — Redis Queue**) and the cache. The backend
enqueues `analyze_repository(repo_id, job_id)`; a separate worker service consumes it.

## Alternatives considered
- **Celery** — more features (chords, beat) but heavier config; overkill here.
- **Cloud queues (SQS, Pub/Sub)** — adds a cloud dependency and cost; not free-tier-simple.
- **DB-backed queue** — possible but reinvents locking/visibility; Redis is purpose-built.

## Consequences
- (+) Tiny footprint; one dependency doubles as queue + cache.
- (+) Free managed option (Upstash) with TLS.
- (+) RQ is dead-simple to operate and debug.
- (−) RQ has fewer orchestration primitives than Celery.
- (−) At-least-once semantics + worker crashes require app-level safety → handled by the
  unique active-job index + heartbeat reaper (see [0010](0010-job-safety.md)).
