# Feature: Repository Analysis

## What it does
Runs the static-analysis pipeline in a background worker and streams progress to the UI.
Produces the dependency graph, complexity metrics, dead-code findings, architecture layers,
and the RAG vector index.

## Why it exists
Analysis is slow (clone + multi-language parse + persist + embed). It must not block the
API, must survive worker crashes, and must never run twice for the same repo concurrently.

## User workflow
1. After submission (or clicking "Re-analyze"), the dashboard opens an SSE progress stream.
2. A progress bar + message advance through stages (clone → parse → graph → … → done).
3. On `succeeded`, insight pages and chat unlock; on `failed`, an error + retry shows.

## Backend implementation
- **Route:** `POST /repositories/{id}/analyze` → `AnalysisService.trigger` creates a
  `QUEUED` job and enqueues it; `409` if one is already active.
- **Progress:** `GET /repositories/{id}/events` (SSE) polls the job row ~1s and emits
  `AnalysisProgressEvent`s until a terminal state.
- **Reaper:** `analysis_reaper` (in app lifespan) fails stale `RUNNING`/`QUEUED` jobs.

## Worker implementation
`worker.app.tasks.analyze_repository.run(repo_id, job_id)`:
1. Mark job `RUNNING`, repo `ANALYZING`, write `heartbeat_at`.
2. Clone (depth-1), capture commit hash.
3. `AnalysisOrchestrator.run_on_path(workspace)` → `RepositoryAnalysis`.
4. Persist (atomic delete+insert of files/symbols/metrics/dependencies + cached stats +
   version stamps).
5. Index chunks into ChromaDB (best-effort; `IndexingDegraded` is non-fatal).
6. Mark job `SUCCEEDED`, repo `READY`, set `analyzed_at`.

Full pipeline: [../architecture/analysis-pipeline.md](../architecture/analysis-pipeline.md).

## Frontend implementation
- `useAnalysisProgress(repoId, enabled)` consumes the SSE stream;
  `AnalysisProgress` renders the bar; `AnalysisGate` blocks insight pages until ready;
  `AnalysisFreshnessBanner` warns when version stamps are stale.

## Tables involved
- `analysis_jobs` (lifecycle + progress + heartbeat), `repositories` (status + stats +
  stamps), `source_files`/`symbols`/`metrics`/`dependencies` (results).

## APIs
`POST /repositories/{id}/analyze`, `GET /repositories/{id}/jobs`,
`GET /repositories/{id}/jobs/latest`, `GET /repositories/{id}/events` (SSE).

## Edge cases handled
- **Duplicate analyze** → `409` via `uq_active_job_per_repository`.
- **Worker crash** → heartbeat stale → reaper marks FAILED.
- **Indexing failure** → job still SUCCEEDS; chat degraded until re-index.
- **Partial write** → single-transaction persistence.
- **Stale analysis** → version stamps + freshness banner + re-analyze.

## Security considerations
- `verify_repository_access` gates analyze + reads (owner or public).
- Clones run under a tmp workspace with size/file limits.

## Future improvements
- Per-function (symbol/call) dependency edges.
- Incremental re-analysis (only changed files).
- Push-triggered re-analysis.
