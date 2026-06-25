# Analysis Pipeline

How a submitted repository becomes structured, queryable, AI-indexed data. This is the
single most important pipeline in the system.

## Stages

```mermaid
flowchart LR
  A[clone] --> B[walk] --> C[parse - parallel] --> D[graph] --> E[metrics] --> F[dead code] --> G[architecture] --> H[persist] --> I[index - best effort] --> J[done]
```

Implemented by `AnalysisOrchestrator.run()` in
[analysis-engine/engine/orchestrator.py](../../analysis-engine/engine/orchestrator.py),
driven by the worker task
[worker/worker/app/tasks/analyze_repository.py](../../worker/worker/app/tasks/analyze_repository.py).

| Stage | Module | Output | Progress band |
| --- | --- | --- | --- |
| Clone | [engine/cloning/git_cloner.py](../../analysis-engine/engine/cloning/git_cloner.py) | working dir + commit hash (depth-1) | 0–10% |
| Walk | [engine/walker/file_walker.py](../../analysis-engine/engine/walker/file_walker.py) | list of analyzable files (respects size/file limits) | 10–20% |
| Parse | [engine/parsers/registry.py](../../analysis-engine/engine/parsers/registry.py) | `FileAnalysis` per file (symbols, imports, metrics) | 20–60% |
| Graph | [engine/graph/builder.py](../../analysis-engine/engine/graph/builder.py) | `DependencyEdge[]` + cycles | 60–70% |
| Metrics | (in parsers + aggregation) | `FileMetrics` per file | 70–75% |
| Dead code | [engine/dead_code/detector.py](../../analysis-engine/engine/dead_code/detector.py) | `DeadCodeFinding[]` | 75–80% |
| Architecture | [engine/architecture/classifier.py](../../analysis-engine/engine/architecture/classifier.py) | layers + Mermaid | 80–85% |
| Persist | [worker/worker/app/persistence.py](../../worker/worker/app/persistence.py) | rows in Postgres | 85–92% |
| Index | [worker/worker/app/ai_runtime.py](../../worker/worker/app/ai_runtime.py) → `RagChain.index_repository` | chunks in ChromaDB | 92–99% |

## Parser strategy (multi-language, graceful)

Resolution order in the registry:
1. **PythonAstParser** — native `ast` for Python (most accurate).
2. **TreeSitterParser** — for `javascript`, `typescript`, `go`, `rust`, `java`, `c`,
   `cpp`, `csharp`, `ruby` (when the tree-sitter grammar is available).
3. **RegexParser** — last-resort heuristic so *no* file is left unanalyzed.

Each parser yields a uniform `FileAnalysis` so downstream stages are language-agnostic.

## Dependency graph building

`engine/graph/builder.py` resolves each raw import target to a concrete file in the repo:
relative-path resolution, module-path resolution, then bare-name fuzzy matching. Edge
kinds in the model are `import | inheritance | call | instantiation | reference`, but in
practice the current analyzers emit **file-level `import` edges** (this is the documented
limitation behind the graph — see [../decisions/0008-dependency-graph.md](../decisions/0008-dependency-graph.md)).
Cycles are detected by [engine/graph/cycles.py](../../analysis-engine/engine/graph/cycles.py).

## Persistence (atomic re-analysis)

`worker/app/persistence.py` writes results so that **re-analysis is idempotent**:

1. Delete the repo's existing `source_files` (cascades to `symbols`, `metrics`,
   `dependencies`).
2. Bulk-insert new `source_files`, then `symbols`, `metrics`, and `dependencies`.
3. Update the `repositories` row: `file_count`, `total_lines`, `languages`, `commit_hash`,
   `analyzed_at`, and the version stamps + `embedding_model`.

All within one transaction → a failed re-analysis never leaves a half-written graph.

## Indexing (best-effort RAG prep)

After persistence, the worker chunks source code, embeds the chunks, and upserts them into
the repo's Chroma collection `repo_<repository_id>`. If Chroma or the embedding provider is
unreachable, the worker raises/handles `IndexingDegraded`: the job still **SUCCEEDS** (the
structural analysis is valuable on its own); only AI chat is degraded until a successful
re-index. Detail: [../ai/rag-pipeline.md](../ai/rag-pipeline.md).

## Progress & heartbeat

[worker/worker/app/progress.py](../../worker/worker/app/progress.py)'s `DbProgressReporter`
maps fine-grained engine events to the coarse `analysis_jobs.progress` (0–100) using the
bands above, throttled (default every ~25 files). Every write also bumps
`analysis_jobs.heartbeat_at`, which the backend reaper uses to detect a dead worker.

## Job safety & recovery

| Risk | Mechanism |
| --- | --- |
| Two analyses at once | `uq_active_job_per_repository` partial unique index → second enqueue is `409` |
| Worker dies mid-job | `heartbeat_at` goes stale → `analysis_reaper.reap_stale_jobs` marks job + repo FAILED |
| Job stuck in QUEUED | `ANALYSIS_QUEUED_TIMEOUT_SECONDS` → reaped |
| Partial write | single-transaction persistence (delete+insert) |

## Tuning knobs (env)

| Variable | Effect |
| --- | --- |
| `API_MAX_REPO_SIZE_MB`, `API_MAX_REPO_FILES` | Reject oversized repos early |
| `WORKER_CONCURRENCY` | Parallel jobs per worker |
| `WORKER_JOB_TIMEOUT_SECONDS` | Hard job timeout |
| `ANALYSIS_RUNNING_HEARTBEAT_TIMEOUT_SECONDS` | When a RUNNING job is considered dead |
| `ANALYSIS_QUEUED_TIMEOUT_SECONDS` | When a QUEUED job is considered abandoned |
| `AI_TOP_K_CHUNKS`, `AI_MAX_CONTEXT_TOKENS` | Retrieval breadth / prompt budget |
