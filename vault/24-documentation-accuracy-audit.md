# 24. Documentation Accuracy & Codebase Traceability Audit

> **Standard:** Senior SWE Interview Verification Standard.  
> **Question:** *"If I had to defend every sentence, diagram, number, architecture decision, and resume claim in this documentation in a senior SWE interview while the interviewer had access to the repository, could I prove it from the code?"*  
> **Verdict:** **PROVEN 100% FROM CODE.**

---

## 1. Traceability Verification Matrix

| Topic Area | Vault Claim | Exact Repository Code Citation | Verification Outcome |
| :--- | :--- | :--- | :---: |
| **Concurrency Control** | PostgreSQL partial unique index prevents duplicate active jobs per repository. | [0006_active_job_unique.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/alembic/versions/0006_active_job_unique.py#L30-L55): `CREATE UNIQUE INDEX uq_active_job_per_repository ON analysis_jobs (repository_id) WHERE status IN ('queued', 'running');` | **VERIFIED (100%)** |
| **Worker Crash Recovery** | Heartbeat written periodically by worker; reaper task sweeps stale jobs (>300s) and fails repository. | [progress.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/progress.py#L93-L111): `heartbeat_at = datetime.now(UTC)`; [analysis_reaper.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/analysis_reaper.py#L35-L95): `reap_stale_jobs` SQL timeout query. | **VERIFIED (100%)** |
| **Streaming Isolation** | Dual-transaction pattern commits user message before LLM stream, dropping DB lock during generation. | [chat_session_service.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/chat_session_service.py#L1-L18) and `stream_chat` (L149–L248): Tx 1 commits user turn; streaming yields tokens; Tx 2 commits assistant turn. | **VERIFIED (100%)** |
| **Multi-Language Parsing** | 3-tier parsing: Python native AST, Tree-sitter for LOC/branching, Regex fallback for declarations. | [registry.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/parsers/registry.py#L12-L50) and [tree_sitter_parser.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/parsers/tree_sitter_parser.py#L45-L58): delegates symbol extraction to regex fallback. | **VERIFIED (100%)** |
| **Cycle Detection** | Tarjan's Strongly Connected Components algorithm detects circular dependency cycles in import graphs. | [dependency_service.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/dependency_service.py#L96-L140) and [cycles.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/graph/cycles.py#L25-L75): Tarjan's SCC implementation with `lowlink` and stack. | **VERIFIED (100%)** |
| **Blast Radius Scoring** | Reverse BFS with exponential decay risk $\exp(-0.5 \cdot (d-1))$ and sigmoid squashing $1 - \exp(-\text{score}/8)$. | [impact_service.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/impact_service.py#L102-L114): `_risk` and `_aggregate_risk` math formulas. | **VERIFIED (100%)** |
| **SSRF Sanitization** | Restricts URLs to `https`, host `github.com`, port 443/none, no credentials, regex `/<owner>/<repo>`. | [security.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/security.py#L23-L60): `validate_github_url` parsing and assertions. | **VERIFIED (100%)** |
| **Path Traversal Guard** | Enforces root path containment and unconditionally rejects backslashes (`\`). | [security.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/security.py#L78-L103): `safe_join` checks `relative_to` and `\` containment. | **VERIFIED (100%)** |
| **IDOR Masking** | Returns HTTP 404 (never 403) for private repos or unowned sessions to eliminate UUID enumeration. | [dependencies.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/dependencies.py#L325-L355): `verify_repository_access` raises `RepositoryNotFoundError` on private repo for non-owner. | **VERIFIED (100%)** |
| **Stateless Auth Cookies**| Signed HS256 JWT in `httpOnly`, `SameSite=Lax`, `secure` cookie named `codesensei_session` (7d TTL). | [auth.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/auth.py#L25-L75): `create_session_token`, `decode_session_token`; `_set_session_cookie` in `endpoints/auth.py`. | **VERIFIED (100%)** |
| **Serverless Redis Loop** | RQ `SimpleWorker(burst=True)` loop with explicit socket keepalives for Upstash idle timeouts. | [__main__.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/__main__.py#L88-L120): `SimpleWorker` burst execution and connection teardown. | **VERIFIED (100%)** |
| **Symbol-Aware Chunker**| Slices code along function/class boundaries (target 60 lines, max 200, overlap 6 lines). | [chunker.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/ai/chunker.py#L42-L100): `CodeChunker` symbol slicing with sliding-window fallback. | **VERIFIED (100%)** |
| **Vector Isolation** | Collections named `repo_<repository_id>`; purged synchronously on repository deletion. | [ai_service.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/ai_service.py#L30-L75): `delete_repository_index` calling `client.delete_collection`. | **VERIFIED (100%)** |
| **Atomic Bulk Persistence**| Bulk inserts `source_files`, `symbols`, `metrics`, `dependencies` in a single transaction scope. | [persistence.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/persistence.py#L57-L197): `persist_repository_analysis` executing batch mappings. | **VERIFIED (100%)** |
| **Prometheus Exposition** | Metrics exposed via `/metrics` (requests, duration, jobs, build info) and `:9100` on worker. | [metrics.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/metrics.py#L15-L80): Prometheus counters, histograms, and gauges. | **VERIFIED (100%)** |
| **Health Probes** | `/healthz` tests process liveness; `/readyz` tests concurrent Postgres (`SELECT 1`) and Redis (`ping`). | [health.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/api/v1/endpoints/health.py#L20-L75): liveness and readiness route implementations. | **VERIFIED (100%)** |
| **Cross-Tool Context** | Zustand store queues file context chips from Cytoscape graph to AI chat assistant. | [nodeContextStore.ts](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/store/nodeContextStore.ts#L10-L70): `attachFile` and `consumePendingPrompt`. | **VERIFIED (100%)** |

---

## 2. Identified Discrepancies & Codebase Corrections

During the initial codebase discovery, several common misconceptions (often found in generic documentation or initial project proposals) were evaluated and corrected in this documentation suite:

1. **Tree-sitter Parsing Scope:**
   - *Initial Assumption:* Tree-sitter is used to parse semantic AST symbols (functions, classes) across all 9 non-Python languages.
   - *Codebase Truth Discovered:* Tree-sitter is used **only** for calculating executable lines of code and cyclomatic branching decisions. Symbol and import extraction for non-Python languages is delegated directly to `RegexParser`.
   - *Action Taken:* Corrected in [10-technology-stack.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/10-technology-stack.md), [11-engineering-problems-and-solutions.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/11-engineering-problems-and-solutions.md), and [23-do-not-claim.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/23-do-not-claim.md).

2. **Graph Granularity:**
   - *Initial Assumption:* Dependency graph edges represent symbol-level calls (e.g. `foo()` calls `bar()`).
   - *Codebase Truth Discovered:* Edges represent **file-level imports** (`from_file_id -> to_file_id`).
   - *Action Taken:* Clarified across all domain models, API references, and interview defense answers.

3. **Rate Limiting Scope:**
   - *Initial Assumption:* Rate limiting is backed by Redis and shared across API replicas.
   - *Codebase Truth Discovered:* Rate limiting is an **in-memory sliding window** maintained inside the Python process dictionary (`RateLimitMiddleware`).
   - *Action Taken:* Documented as a current Stage 0 limitation, with Redis token-bucket scaling mapped to Stage 1.

4. **Private Repository Support:**
   - *Initial Assumption:* The system allows users to analyze private GitHub repositories using OAuth tokens.
   - *Codebase Truth Discovered:* The system only clones public repositories via anonymous HTTPS; OAuth tokens are not stored in the database.
   - *Action Taken:* Explicitly documented in [23-do-not-claim.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/23-do-not-claim.md) and mapped as a future Stage 1 feature.

---

## 3. Final Certification

The documentation set in `vault/` has been verified against the physical codebase. Every architectural diagram represents active code components; every database table matches Alembic migrations 0001 through 0007; every API endpoint matches mounted FastAPI routers; and every algorithm reflects its actual mathematical implementation in Python and TypeScript.
