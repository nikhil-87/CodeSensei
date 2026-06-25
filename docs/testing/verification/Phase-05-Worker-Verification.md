# Phase 5 — Worker Verification

> *Status: Complete · Tests: 14/14 passing · Engine regressions: 0/57*

This document captures the design decisions, surfaces, execution flow,
and verification commands for **Phase 5 — Worker**. The worker is the
process that consumes the RQ queue produced by the FastAPI backend, runs
the analysis engine over a cloned repository, persists the result into
Postgres, and (best-effort) indexes the source into Chroma for RAG.

---

## 1 — Design decisions

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | **Synchronous SQLAlchemy session** in the worker (mirrors the backend's models, but separate engine) | RQ runs OS threads; an async event loop per task adds latency and complexity. We re-use the *models* but not the *session machinery*. |
| 2 | **Task is registered by import path** (`worker.app.tasks.analyze_repository.run`), matching the backend's `JobDispatcher.ANALYZE_REPOSITORY_JOB` constant | RQ enqueues by string. Both sides agree on one constant; no pickling of callables. |
| 3 | **Worker drives the cloner directly** instead of `AnalysisOrchestrator.run(url)` | The orchestrator clones internally and discards the path; we need the workspace path on disk to read sources for AI indexing. Calling `GitCloner` then `run_on_path(workspace)` keeps both responsibilities explicit. |
| 4 | **Stage-banded progress mapping** (`_STAGE_BANDS` dict in `progress.py`) | Engine reports per-stage `progress(0..1)` callbacks; the UI wants a monotonic 0..100. Each stage maps onto a fixed band (clone 0–10, parse 20–60, index 92–99, etc.) so users see smooth, ordered progress regardless of stage durations. |
| 5 | **File-event throttling** (`worker_progress_throttle_files=25`) | A 5,000-file repo would otherwise issue 5,000 `UPDATE analysis_jobs` calls. Throttling keeps DB write rate bounded while still giving fresh progress messages. |
| 6 | **Idempotent re-runs**: `persist_repository_analysis` deletes prior `SourceFile` rows + cascades, then inserts fresh; AI indexing calls `vector_store.delete_collection()` before `index_repository()` | Re-analysing a repo (e.g. after a `git push`) yields a clean view, never stale rows or accumulated chunks. |
| 7 | **Best-effort AI indexing** — `IndexingDegraded` is caught inside `analyze_repository._try_index` and converted to `indexed_chunks=0` | An Ollama or Chroma outage must not fail the analysis job. Code analysis still ships value (graphs, dead-code, metrics) without the chat feature. |
| 8 | **All progress writes swallow exceptions** (`_write` / `_write_message` / `_factory_scope`) | Progress is a side-effect; a transient DB hiccup must never crash a long-running analysis. |
| 9 | **Late imports for backend models inside the worker package** | The worker package stays importable for linting/CI even when `backend/` is not on `PYTHONPATH`. |
| 10 | **Errors mark *both* job and repository FAILED with truncated `error_message`** (`_mark_failed`) | The UI needs a single source of truth — a failed analysis means the *repository* is in a failed state, not just one of N jobs. |
| 11 | **Backend chat endpoint streams via `AIService` constructed per-request** | RAG state per repository is small (one ChromaCollection); building it on demand keeps the API stateless and avoids cross-request cache invalidation. |
| 12 | **`AIService.stream_chat` translates engine `ChatStreamEvent` → backend `ChatTokenEvent` JSON** | The backend SSE schema is the public contract. The engine remains free to evolve its internal stream events without breaking the frontend. |

---

## 2 — Files generated / modified

### New worker package — `worker/`

| File | Purpose |
|------|---------|
| [worker/pyproject.toml](../worker/pyproject.toml) | Package metadata + console script `codesensei-worker` |
| [worker/Dockerfile](../worker/Dockerfile) | Multi-stage Python 3.12-slim image with `git`, non-root user |
| [worker/README.md](../worker/README.md) | Operator guide (run locally, run tests, ops notes) |
| [worker/worker/__init__.py](../worker/worker/__init__.py) | Namespace marker |
| [worker/worker/app/__init__.py](../worker/worker/app/__init__.py) | Namespace marker |
| [worker/worker/app/__main__.py](../worker/worker/app/__main__.py) | `python -m worker.app` entrypoint — pings Redis then runs RQ Worker |
| [worker/worker/app/settings.py](../worker/worker/app/settings.py) | Pydantic `WorkerSettings` mirroring backend env, sync DSN, workspace_root |
| [worker/worker/app/logging_config.py](../worker/worker/app/logging_config.py) | structlog JSON renderer (matches backend) |
| [worker/worker/app/db.py](../worker/worker/app/db.py) | Sync SQLAlchemy `Engine`, `sessionmaker`, `session_scope`, test hooks |
| [worker/worker/app/exceptions.py](../worker/worker/app/exceptions.py) | `WorkerError`, `JobNotFoundError`, `RepositoryNotFoundError`, `IndexingDegraded` |
| [worker/worker/app/progress.py](../worker/worker/app/progress.py) | `DbProgressReporter` + `mark_job_running/succeeded/failed` lifecycle helpers |
| [worker/worker/app/persistence.py](../worker/worker/app/persistence.py) | `persist_repository_analysis` — translates `RepositoryAnalysis` → ORM rows |
| [worker/worker/app/ai_runtime.py](../worker/worker/app/ai_runtime.py) | `build_runtime`, `read_sources`, `index_with_runtime` |
| [worker/worker/app/tasks/__init__.py](../worker/worker/app/tasks/__init__.py) | Namespace marker |
| [worker/worker/app/tasks/analyze_repository.py](../worker/worker/app/tasks/analyze_repository.py) | The RQ task `run(repository_id, job_id)` — orchestrates clone → analyse → persist → index |
| [worker/tests/__init__.py](../worker/tests/__init__.py) | Marker |
| [worker/tests/conftest.py](../worker/tests/conftest.py) | sqlite in-memory fixtures, `make_repo` / `make_job` factories |
| [worker/tests/test_progress.py](../worker/tests/test_progress.py) | 8 tests: stage bands, monotonic progress, throttling, lifecycle, error swallowing |
| [worker/tests/test_persistence.py](../worker/tests/test_persistence.py) | 3 tests: insert + dead-code + idempotent replace |
| [worker/tests/test_analyze_task.py](../worker/tests/test_analyze_task.py) | 3 tests: success path, indexing degraded, engine error |

### Engine factory — `analysis-engine/`

| File | Purpose |
|------|---------|
| [analysis-engine/engine/ai/factory.py](../analysis-engine/engine/ai/factory.py) | `AIRuntimeConfig`, `AIRuntime`, `build_rag_chain` — shared by backend + worker |
| [analysis-engine/engine/ai/__init__.py](../analysis-engine/engine/ai/__init__.py) | Re-exports the factory symbols |

### Backend wire-up

| File | Change |
|------|--------|
| [backend/app/services/ai_service.py](../backend/app/services/ai_service.py) | New service — async wrapper around `RagChain.stream_chat` |
| [backend/app/api/v1/endpoints/ai.py](../backend/app/api/v1/endpoints/ai.py) | Endpoint now calls `AIService.stream_chat`, emits real SSE events |
| [backend/app/core/dependencies.py](../backend/app/core/dependencies.py) | Added `_make_ai_service` + `AIServiceDep` |

---

## 3 — Execution flow

```text
        Frontend (POST /repositories)
               │
               ▼
        FastAPI backend
        ┌─────────────────────────┐
        │ RepositoryService       │
        │ .create_and_enqueue()   │
        │   ├─ INSERT repository  │
        │   ├─ INSERT job (QUEUED)│
        │   └─ JobDispatcher      │
        └────────────┬────────────┘
                     │
                     │ Queue.enqueue(
                     │   "worker.app.tasks.analyze_repository.run",
                     │   repository_id, job_id)
                     ▼
                Redis (RQ queue)
                     │
                     ▼
        Worker process — `python -m worker.app`
        ┌──────────────────────────────────────────────┐
        │ analyze_repository.run(repo_id, job_id)      │
        │                                              │
        │  1. mark_job_running             (RUNNING)   │
        │  2. set Repository.status=ANALYZING          │
        │  3. stage("clone")                           │
        │     └─ GitCloner.clone(url) → workspace path │
        │  4. AnalysisOrchestrator(reporter=…)         │
        │     └─ run_on_path(workspace)                │
        │         ├─ stage("walk")                     │
        │         ├─ stage("parse")  → file_done()*N   │
        │         ├─ stage("graph")                    │
        │         ├─ stage("metrics")                  │
        │         ├─ stage("dead_code")                │
        │         └─ stage("architecture")             │
        │  5. stage("persist")                         │
        │     └─ persist_repository_analysis(session)  │
        │         ├─ DELETE prior SourceFile rows      │
        │         ├─ INSERT files / metrics / symbols  │
        │         ├─ apply dead-code findings          │
        │         ├─ INSERT deduped dependencies       │
        │         └─ UPDATE Repository (status=READY)  │
        │  6. stage("index")  [best-effort]            │
        │     ├─ build AIRuntime (Chroma + Ollama)     │
        │     ├─ vector_store.delete_collection()      │
        │     └─ chain.index_repository(files,sources) │
        │        └─ on AIError → IndexingDegraded → 0  │
        │  7. stage("done")                            │
        │  8. mark_job_succeeded         (SUCCEEDED)   │
        │                                              │
        │  on EngineError or Exception:                │
        │    _mark_failed(repo_uuid, job_uuid, error)  │
        │    re-raise so RQ records the failure        │
        └──────────────────────────────────────────────┘
                     │
                     │ writes job.progress + progress_message
                     │ throughout (throttled to every 25 files)
                     ▼
                Postgres + Chroma

        Frontend (poll GET /repositories/{id}/jobs/{id})
                     ▲
                     │ status, progress, progress_message
                     │
        Frontend (POST /ai/chat)
                     │
                     ▼
        FastAPI backend
        ┌──────────────────────────────────────────────┐
        │ AIService.stream_chat(req)                   │
        │   build_rag_chain(AIRuntimeConfig)           │
        │   chain.stream_chat(engine_request)          │
        │     ├─ retrieve top-k chunks  (Chroma)       │
        │     ├─ stream tokens         (Ollama)        │
        │     └─ yield events:                         │
        │        citations / token* / done | error     │
        │                                              │
        │ Events translated → ChatTokenEvent JSON      │
        │ Returned via sse-starlette EventSourceResp.  │
        └──────────────────────────────────────────────┘
```

---

## 4 — Verification steps

### 4.1 — Worker test suite (hermetic; no DB / Redis / Ollama needed)

```powershell
cd worker
$env:PYTHONPATH = "$PWD;$PWD\..\backend"
..\analysis-engine\.venv\Scripts\python.exe -m pytest -q
```

**Expected:**

```
..............                                                           [100%]
14 passed in 2.61s
```

The tests cover:

- **Progress (8 tests)** — stage band math, monotonic progress (no slide-back), file-event throttling, three lifecycle helpers, error swallowing on simulated DB outage.
- **Persistence (3 tests)** — file/symbol/metric/edge insertion, dead-code score + `is_used` updates, idempotent replacement on re-run.
- **Analyze task (3 tests)** — happy path (job SUCCEEDED, repo READY, files persisted, 4 chunks indexed); indexing degraded (job still SUCCEEDED, `indexed_chunks=0`); engine error (job FAILED, repo FAILED, error truncated).

### 4.2 — Engine regression check

```powershell
cd analysis-engine
.\.venv\Scripts\python.exe -m pytest -q
```

**Expected:** `57 passed`.

### 4.3 — End-to-end smoke (requires running stack)

```powershell
# Terminal 1 — Postgres + Redis + Chroma
docker compose up postgres redis chroma -d

# Terminal 2 — backend
cd backend
.\.venv\Scripts\uvicorn.exe app.main:app --reload --port 8000

# Terminal 3 — worker
cd worker
.\.venv\Scripts\python.exe -m worker.app

# Terminal 4 — enqueue an analysis
$body = @{ url = "https://github.com/octocat/Hello-World" } | ConvertTo-Json
Invoke-RestMethod -Method POST -Uri http://localhost:8000/api/v1/repositories `
    -ContentType "application/json" -Body $body

# poll the job
Invoke-RestMethod http://localhost:8000/api/v1/repositories  # → list
Invoke-RestMethod http://localhost:8000/api/v1/repositories/<id>/jobs/<job-id>
```

You should see:
- Worker logs: `analyze_started → cloned → parsed N files → persisted_analysis → analyze_completed`.
- Job row: `status=SUCCEEDED, progress=100`.
- Repository row: `status=READY, file_count=N, total_lines=L, languages="python:N"`.

### 4.4 — Chat endpoint smoke

```powershell
$body = @{
    repository_id = "<repo-uuid>"
    question      = "What does this repository do?"
    history       = @()
    top_k         = 8
} | ConvertTo-Json

Invoke-WebRequest -Method POST -Uri http://localhost:8000/api/v1/ai/chat `
    -ContentType "application/json" -Body $body -Headers @{Accept="text/event-stream"} `
    -OutFile chat.sse
Get-Content chat.sse -Tail 30
```

Expected SSE shape:

```
event: citations
data: {"event":"citations","citations":[{"file_path":"src/...","line_start":12,...}]}

event: token
data: {"event":"token","content":"This"}

event: token
data: {"event":"token","content":" repository"}
...

event: done
data: {"event":"done"}
```

If Ollama is offline:

```
event: error
data: {"event":"error","error":"..."}
event: done
data: {"event":"done"}
```

---

## 5 — Operational notes

- **Re-runs are safe.** Triggering a second analysis on the same repository deletes prior `SourceFile` rows (cascade clears Symbols/Metrics/Dependencies) and the prior Chroma collection. There is never duplicate state.
- **AI failures are isolated.** A failed `IndexingDegraded` produces a `WARNING` log and `indexed_chunks=0`; the job still finishes SUCCEEDED.
- **Hard analysis errors mark both rows FAILED.** Look at `analysis_jobs.error` (truncated to 4 KB) and `repositories.error_message` (truncated to 2 KB).
- **Progress writes are best-effort.** A transient DB hiccup during progress reporting only logs a `WARNING` — the analysis itself continues.
- **Backend → worker contract is one constant.** `JobDispatcher.ANALYZE_REPOSITORY_JOB == "worker.app.tasks.analyze_repository.run"`. Don't rename the task without updating both sides.
