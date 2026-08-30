# 12. Reliability & Failure Handling Matrix

> **Status:** Codebase-grounded analysis of error propagation, recovery mechanisms, and failure modes.  
> **Source Verification:** [backend/app/main.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/main.py), [backend/app/services/analysis_reaper.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/analysis_reaper.py), [worker/worker/app/tasks/analyze_repository.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/tasks/analyze_repository.py).

---

## 1. System-Wide Failure Handling Matrix

| Failure Mode | Current Behavior | Handled? | How Handled in Code | Remaining Weakness | Possible Improvement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL Outage** | API endpoints fail with connection errors; `/readyz` probe reports `"degraded"`. | **Partially** | Lifespan logs error; `/readyz` reports failure. Handled gracefully via `_unhandled_handler` returning HTTP 500. | In-flight worker jobs crash; cannot persist analysis results. | Automated connection retry backoff in `get_engine` with circuit breaker. |
| **Redis Outage (Queue)** | Enqueueing fails; API returns HTTP 503 (`QueueUnavailableError`). | **Yes** | `JobDispatcher.enqueue_analysis` catches `redis.exceptions.RedisError`, logs error, raises `QueueUnavailableError`. | New submissions rejected until Redis recovers. | Local disk spooling or SQLite fallback queue during Redis downtime. |
| **Redis Outage (Cache)** | Cache misses fall back directly to PostgreSQL queries. | **Yes** | `RedisCache.get_json` catches errors and returns `None`; services fall back to database queries. | Database experiences increased read load during Redis outage. | In-memory LRU cache fallback (e.g. `cachetools`) inside API process. |
| **Worker OOM / Hard Crash** | Worker process dies; job remains `running` until timeout. | **Yes** | `AnalysisReaper` runs every 60s by default, marks jobs with stale heartbeats (>900s) or unstarted queue jobs (>1800s) as `failed`, flips repository to `failed`. | Up to 900 seconds delay before the user sees the failure and can retry. | Decrease heartbeat timeout to 60s for small repositories; register SIGTERM handlers. |
| **Duplicate Concurrent Analysis** | Second request attempts to insert duplicate active job. | **Yes** | DB partial unique index `uq_active_job_per_repository` throws `IntegrityError`; service maps to HTTP 409. | None — absolute consistency guaranteed at SQL level. | Frontend preemptively disables submit button during in-flight submission. |
| **GitHub Clone Timeout** | Git clone hangs due to network lag or massive git history. | **Yes** | `GitCloner` sets `CLONE_TIMEOUT_SECONDS=300` (default); terminates process and raises `CloneError`. | Consumes up to 300s of worker execution time before terminating. | Implement streaming git clone progress or pre-flight HEAD checks for repo size. |
| **Oversized Repository (>500MB)** | Clone exceeds disk limit. | **Yes** | `GitCloner` monitors cloned directory size, raises `RepositoryTooLargeError` (default `API_MAX_REPO_SIZE_MB=500`), marks job and repo `failed`. | Cloned bytes must be written to disk before size check aborts. | Execute GitHub API pre-check on `size` field prior to cloning. |
| **Malformed Code / Encoding Error** | File contains invalid UTF-8 or corrupt bytes. | **Yes** | `_decode()` runs UTF-8 decode, falls back to `chardet` Latin-1 guess; un-decodable files return `None` and are skipped. | High chardet CPU cost on very large binary files misidentified as code. | Use fast Rust-based encoding detectors or `magic` byte checks. |
| **Parser Syntax Error / Crash** | A single file contains invalid syntax or crashes Tree-sitter. | **Yes** | `ParserRegistry.parse()` catches exceptions in Tier 1/2, falls back to Tier 3 Regex; if regex fails, returns empty metrics. | File metrics may record LOC=0 and missing symbols. | Log warning with file path for parser grammar improvement. |
| **ChromaDB Outage (Indexing)** | Worker cannot connect to ChromaDB to upsert chunk vectors. | **Yes** | `_try_index` catches `IndexingDegraded`, logs warning, returns `indexed_chunks=0`. **Job still SUCCEEDS.** | Code graph and complexity features work, but AI chat has no vectors to search. | Store pending embedding batches in a queue to re-index when Chroma recovers. |
| **Groq Cloud API Rate Limit (429)** | LLM API rejects chat request with rate limit exceeded. | **Yes** | `AIService.stream_chat` catches exception, logs it, yields SSE `error` event followed by clean `done` terminator. | User receives "The assistant ran into a problem" error message. | Automatic fallback to local Ollama or secondary cloud provider (Anthropic/OpenAI). |
| **HuggingFace Inference API Timeout**| Vector embedding generation times out or fails. | **Yes** | `FreeEmbeddings` raises `EmbeddingError`; worker catches and converts to `IndexingDegraded`. Job still succeeds. | Vector index is not built for that repository run. | Local CPU `sentence-transformers` automatic fallback when cloud API times out. |
| **Client Disconnect Mid-Stream** | User closes browser while LLM answer is streaming. | **Yes** | **Dual-Transaction Pattern:** User question was already committed in Tx 1. LLM stream aborts cleanly. | Assistant response is not saved to history. | Background task completes LLM stream and persists assistant turn even after disconnect. |
| **JWT Session Expiration** | User makes a request after 7-day token expiration. | **Yes** | `decode_session_token` returns `None`; `CurrentUserDep` raises `UnauthorizedError` (HTTP 401). | User must re-authenticate; uncommitted frontend form inputs may be lost. | Implement silent session refresh or refresh token rotation before expiry. |
| **Partial Repository Analysis Run** | Worker crashes while inserting symbols and metrics. | **Yes** | `persist_repository_analysis` executes within a single database transaction (`with session_scope()`). Rolls back on error. | None — atomic all-or-nothing database persistence. | Already optimal. |
| **Stale Upstash Redis TCP Connection** | Serverless Redis terminates idle persistent socket. | **Yes** | Worker operates in `SimpleWorker(burst=True)` mode: creates connection, runs burst, closes connection. | 5-second polling interval delay when new jobs arrive. | Already optimal for serverless tier. |
| **SSRF Ingestion Attack** | Attacker submits `http://169.254.169.254` (cloud metadata). | **Yes** | `validate_github_url` rejects non-HTTPS schemes and hosts other than `github.com`. Raises HTTP 400. | None. | Already optimal. |
| **Path Traversal Attack** | Malicious repo path `../../etc/passwd`. | **Yes** | `safe_join` enforces resolution within workspace root and rejects backslashes (`\`). Raises `PathTraversalError`. | None. | Already optimal. |

---

## 2. Deep Dive: The 3 Critical Self-Healing Subsystems

### 2.1 The Two-Phase Atomic Persistence Pattern
In `worker/worker/app/persistence.py`, repository analysis persistence is wrapped in a single relational transaction:
1. `DELETE FROM source_files WHERE repository_id = :id` cascades deletions across `symbols`, `dependencies`, and `metrics`.
2. Batch `INSERT` statements re-populate `source_files`, `symbols`, `metrics`, and `dependencies`.
3. `UPDATE repositories SET status = 'ready', ...` commits the new version stamps and statistics.
- **Resilience Guarantee:** If an exception occurs at any point during step 2 (e.g., unique edge constraint violation), the transaction rolls back completely. The repository does not enter a corrupted partial state.

### 2.2 Graceful Vector Store Degradation
In `worker/worker/app/tasks/analyze_repository.py`, vector indexing is treated as an optional enhancement to static analysis:
```python
# Stage 4: Persist into Postgres (MANDATORY)
with session_scope() as session:
    counts = persist_repository_analysis(session, repository_id=repo_uuid, analysis=analysis)

# Stage 5: Best-effort vector indexing (OPTIONAL)
indexed_chunks = 0
if cfg.worker_indexing_enabled:
    indexed_chunks = _try_index(cfg, repo_uuid, analysis, workspace)
```
If ChromaDB is offline, or if the HuggingFace API key is missing or rate-limited:
- `_try_index` catches `IndexingDegraded` and returns `0`.
- The worker proceeds to mark the repository `READY`.
- The user can still view the Dependency Graph, Complexity rankings, Dead Code report, and Architecture diagrams. Only the AI chat will lack search context.

### 2.3 Heartbeat-Driven Zombie Reaper
In `backend/app/services/analysis_reaper.py`, the reaper eliminates "zombie" jobs:
- **Liveness Signal:** The worker writes `heartbeat_at = now()` whenever it starts a new stage or completes 25 files.
- **Reaper Execution:** Every 30 seconds, the backend queries for active jobs whose last heartbeat is older than `analysis_running_heartbeat_timeout_seconds` (300s).
- **Atomic Release:** The reaper updates the job to `FAILED` and the repository to `FAILED`. This automatically clears PostgreSQL's `uq_active_job_per_repository` index, unblocking the repository for immediate user re-analysis.
