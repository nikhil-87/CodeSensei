# Worker

RQ worker that drives the analysis engine and the AI indexing pipeline.
The backend never imports task functions directly — it enqueues by
string (`worker.app.tasks.analyze_repository.run`) so the worker can
evolve independently.

## What it does

For each `analyze_repository` job:

1. Mark the `AnalysisJob` row as `RUNNING`.
2. Clone the repository into the workspace via `engine.GitCloner`.
3. Run `engine.AnalysisOrchestrator.run_on_path` against the clone.
4. Persist the `RepositoryAnalysis` (files, symbols, metrics, edges,
   dead-code) into Postgres in a single transaction.
5. **Best-effort**: chunk every source file, embed via the configured
   embedding provider (HuggingFace, local, or Ollama), upsert
   into ChromaDB through `engine.ai.RagChain.index_repository`. AI
   infra outages are logged but do not fail the job.
6. Mark the job `SUCCEEDED` (or `FAILED` on hard error). The
   `Repository.status` is updated in lock-step.

Progress is reported back to the `analysis_jobs` row by a
`DbProgressReporter` that the SSE endpoint streams to the frontend.

## Layout

```
worker/
├── pyproject.toml
├── Dockerfile
├── README.md
└── worker/
    └── app/
        ├── __main__.py                      # python -m worker.app
        ├── settings.py                      # WorkerSettings (Pydantic)
        ├── logging_config.py                # structlog + JSON
        ├── db.py                            # sync SQLAlchemy session
        ├── ai_runtime.py                    # build_runtime + index_with_runtime
        ├── persistence.py                   # RepositoryAnalysis → ORM rows
        ├── progress.py                      # DbProgressReporter + lifecycle helpers
        ├── exceptions.py                    # WorkerError, IndexingDegraded
        └── tasks/
            └── analyze_repository.py        # the RQ task entry point
```

## Run locally

```powershell
cd worker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ../analysis-engine
pip install -e .[dev]

# Backend models must be on PYTHONPATH so the worker can import them.
$env:PYTHONPATH="$PWD\..\backend;$PWD"

# .env should match the backend's; redis/postgres/ollama/chroma must be reachable.
python -m worker.app
```

## Run tests

```powershell
cd worker
.\.venv\Scripts\Activate.ps1
pytest -q
```

The tests are hermetic — no Redis, no Postgres, no Ollama, no Chroma.
A SQLite engine substitutes for Postgres; fakes substitute for the
AI infra (re-using the engine's test fakes).

## Operations

* The worker is **stateless** — it owns no on-disk state apart from
  `worker_clone_dir` (default `/var/lib/codesensei/workspaces`).
* Jobs are idempotent: re-running an `analyze_repository` job for the
  same `repository_id` deletes prior `SourceFile` rows (cascade kills
  symbols, metrics, deps) and the prior Chroma collection before
  re-indexing.
* Indexing failures are isolated. A repository can be analysed and
  show up in the API even when Ollama or ChromaDB is unreachable.
