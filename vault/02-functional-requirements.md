# 02. Functional Requirements — Implemented vs. Proposed

> **Status:** Derived directly from active API routes, ORM models, background workers, and frontend components.  
> **Source Verification:** [backend/app/api/v1/endpoints/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/api/v1/endpoints/), [worker/worker/app/tasks/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/tasks/), [analysis-engine/engine/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/).

---

## 1. Implemented Functional Requirements

### 1.1 Authentication & User Management
- **FR-AUTH-01 (GitHub OAuth Login):** Users can authenticate via GitHub OAuth 2.0. The system initiates an authorization redirect (`GET /api/v1/auth/github/login`) with an anti-CSRF state cookie, handles the GitHub callback (`GET /api/v1/auth/github/callback`), exchanges the authorization code for an access token, fetches the user's GitHub profile, and upserts a record in the `users` table.
- **FR-AUTH-02 (Stateless Session Cookie):** The system issues an `httpOnly`, `SameSite=Lax` signed JWT session cookie containing `user_id` and `github_login` with a default TTL of 7 days (604,800 seconds).
- **FR-AUTH-03 (Current User Profile):** Authenticated users can fetch their own profile details (`GET /api/v1/auth/me`).
- **FR-AUTH-04 (Logout):** Users can terminate their session (`POST /api/v1/auth/logout`), which explicitly deletes the session cookie.
- **FR-AUTH-05 (Local Development Login):** In non-production environments (`APP_ENV != production` and `AUTH_DEV_LOGIN_ENABLED = true`), developers can log in without GitHub OAuth credentials by specifying a username (`POST /api/v1/auth/dev-login`). The system generates a deterministic negative fake GitHub ID. This endpoint hard-fails with 404 in production.
- **FR-AUTH-06 (Mock Auth Bypass):** In non-production environments with `MOCK_AUTH = true`, every request is automatically signed in as a configured mock user, bypassing login screens entirely. This is hard-disabled when `APP_ENV = production`.

### 1.2 Repository Submission & Ingestion
- **FR-REPO-01 (Repository Submission):** Authenticated users can submit a public GitHub repository by URL and optional branch (`POST /api/v1/repositories`).
- **FR-REPO-02 (SSRF & URL Validation):** The system validates all URLs: scheme must be `https`, host must be `github.com`, port must be 443/omitted, credentials and query parameters are forbidden, and the path must conform to `/<owner>/<repo>`.
- **FR-REPO-03 (Per-User Repository Isolation):** Each user maintains their own independent record of an analyzed repository `(owner_id, url, branch)`. If a user re-submits a repo they already have, the system returns the existing record instead of creating duplicates.
- **FR-REPO-04 (Visibility Control):** Repository owners can toggle their repository between private (`is_public = false`, visible only to owner) and public (`is_public = true`, visible read-only to anyone with the link) via `PATCH /api/v1/repositories/{id}/visibility`.
- **FR-REPO-05 (Repository Deletion & Vector Cleanup):** Owners can delete a repository (`DELETE /api/v1/repositories/{id}`). The database cascades deletion of source files, symbols, dependencies, metrics, jobs, stars, and chat sessions. The backend synchronously purges the corresponding vector collection in ChromaDB.
- **FR-REPO-06 (Repository Listing):** Users can list their submitted repositories with pagination and status filters (`GET /api/v1/repositories`).
- **FR-REPO-07 (Repository Detail):** Users can view single repository details (`GET /api/v1/repositories/{id}`). Access is permitted if the caller is the owner or if the repository is marked public. Non-owners accessing private repositories receive a 404.

### 1.3 Static Code Analysis & Worker Pipeline
- **FR-ANALYSIS-01 (Asynchronous Enqueueing):** Submitting a repository creates an `analysis_jobs` record with status `queued` and enqueues a job into Redis RQ.
- **FR-ANALYSIS-02 (Active Job Mutual Exclusion):** At most one `queued` or `running` analysis job may exist per repository at any time. Violations raise an integrity error mapped to HTTP 409 (`analysis_already_running`).
- **FR-ANALYSIS-03 (Re-Analysis Trigger):** Users can manually re-trigger analysis for an existing repository (`POST /api/v1/repositories/{id}/analyze`).
- **FR-ANALYSIS-04 (Real-Time Progress Streaming):** Clients can stream live job status updates over Server-Sent Events (`GET /api/v1/repositories/{id}/events`), receiving granular stage events: `queued`, `running`, `progress` (0–100%), `succeeded`, and `failed`.
- **FR-ANALYSIS-05 (Sandboxed Git Cloning):** The worker clones the repository with `depth=1` and applies a clone timeout (default 120s) and repository size limit (default 100MB).
- **FR-ANALYSIS-06 (Multi-Language AST Parsing):** The analysis engine parses files using a 3-tier fallback strategy:
  1. Python native AST parser for `.py` files.
  2. Tree-sitter parser for TypeScript, JavaScript, Go, Rust, Java, C, C++, C#, and Ruby (extracting accurate LOC and branch counts).
  3. Regex fallback parser extracting symbols and import patterns.
- **FR-ANALYSIS-07 (Dependency Graph & Cycle Detection):** The engine resolves imports into directed dependency edges. Tarjan's Strongly Connected Components algorithm detects circular dependency cycles across files.
- **FR-ANALYSIS-08 (Code Complexity Scoring):** The system computes cyclomatic complexity, cognitive complexity, lines of code, function counts, and class counts for every source file.
- **FR-ANALYSIS-09 (Dead Code Detection):** The system identifies unreferenced symbols and computes a `dead_code_score` per file, differentiating internal unreferenced symbols (confidence 0.95) from unused exported symbols (confidence 0.60).
- **FR-ANALYSIS-10 (Architecture Layer Discovery):** The engine classifies files into architectural layers (`controllers`, `services`, `repositories`, `models`, `infrastructure`, `ui`, `tests`) and top-level components, outputting valid Mermaid flowchart diagrams.
- **FR-ANALYSIS-11 (Atomic Persistence):** Worker wipes prior analysis rows (`source_files`, `symbols`, `dependencies`, `metrics`) and re-inserts the newly parsed run atomically within a database transaction.
- **FR-ANALYSIS-12 (Stuck-Job Reaper):** The worker periodically writes `heartbeat_at` timestamps to the job row. A background reaper loop running in the API checks for jobs with expired heartbeats (>300s) or unstarted queued jobs (>900s), marking them failed and releasing the active-job lock.

### 1.4 Intelligence & Exploration Features
- **FR-INTEL-01 (Dependency Graph Inspection):** Clients can retrieve the full dependency graph (`GET /api/v1/repositories/{id}/dependencies`) including nodes, edges, in/out degrees, and detected cycle groupings. Responses are cached in Redis.
- **FR-INTEL-02 (Complexity Rankings):** Clients can retrieve top-N most complex files ranked by cyclomatic or cognitive complexity (`GET /api/v1/repositories/{id}/complexity?top_n=10`).
- **FR-INTEL-03 (Dead Code Report):** Clients can query detected unused symbols, file paths, line numbers, and confidence metrics (`GET /api/v1/repositories/{id}/dead-code`). Responses are cached in Redis.
- **FR-INTEL-04 (Impact Analysis / Blast Radius):** Users can supply a file path to calculate the upstream blast radius (`POST /api/v1/repositories/{id}/impact`). The system runs a reverse-dependency BFS up to `max_depth`, calculating an aggregate risk score via exponential decay and sigmoid saturation.
- **FR-INTEL-05 (Architecture Map):** Clients can retrieve layer groupings, component counts, and generated Mermaid diagrams (`GET /api/v1/repositories/{id}/architecture`). Responses are cached in Redis.
- **FR-INTEL-06 (Fact-Grounded Documentation Generation):** Clients can generate markdown documentation (`POST /api/v1/repositories/{id}/documentation`) across six templates: `readme`, `architecture`, `api`, `onboarding`, `technical_design`, and `summary`. Content is generated purely from database metrics without LLM latency.

### 1.5 Conversational AI & RAG Pipeline
- **FR-AI-01 (Symbol-Aware Chunking):** The engine chunks source code aligned with symbol boundaries (target 60 lines, max 200 lines, overlap 6 lines, minimum 40 characters) with a sliding window fallback.
- **FR-AI-02 (Semantic Code Indexing):** The worker embeds chunks and upserts them into ChromaDB collections named `repo_<repository_id>` with metadata (`file_path`, `language`, `line_start`, `line_end`, `symbol_name`, `symbol_kind`).
- **FR-AI-03 (Stateless Streaming Chat):** Users can stream answers to ad-hoc codebase questions (`POST /api/v1/ai/chat`) over SSE. The system retrieves top-k chunks from ChromaDB, constructs a system prompt, and streams LLM tokens from Groq or Ollama.
- **FR-AI-04 (Persistent Chat Sessions):** Users can create private, multi-turn chat sessions (`POST /api/v1/repositories/{id}/chat-sessions`), list them, rename them, and delete them. Sessions are strictly scoped to the authenticated user and hidden behind 404 for other users.
- **FR-AI-05 (Session Chat Streaming & Dual-Transaction Persistence):** Sending a message in a session (`POST /api/v1/chat-sessions/{id}/chat`) streams tokens and citations over SSE. Transaction 1 commits the user message before streaming starts; Transaction 2 commits the assistant response and citations after streaming ends.
- **FR-AI-06 (Context Tagging):** Users can explicitly attach file context chips ("Ask AI about this file"). Attached files are guaranteed inclusion in the retrieval context regardless of vector similarity score.

### 1.6 Social & Discovery Hub
- **FR-SOC-01 (Repository-Centric Public Discovery):** Anyone can browse publicly analyzed repositories (`GET /api/v1/discover/repositories`), grouped by `(url, branch)`. Supports sorting by stars, file count, total lines, or recent updates, and filtering by keyword or language.
- **FR-SOC-02 (Repository Group Detail):** Clients can view all public analyses performed on a given URL/branch by different analysts (`GET /api/v1/discover/repository`).
- **FR-SOC-03 (Repository Starring):** Authenticated users can star or unstar repositories (`PUT/DELETE /api/v1/repositories/{id}/star`). Starring is idempotent and updates a denormalized `star_count` on the repository row.
- **FR-SOC-04 (User Starred List):** Users can view repositories they have starred (`GET /api/v1/me/stars`).
- **FR-SOC-05 (Public User Profiles):** Anyone can view an analyst's public profile and their public analyses (`GET /api/v1/users/{username}` and `GET /api/v1/users/{username}/repositories`).

---

## 2. Potential Future / Proposed Requirements

These features are architectural evolutions not implemented in the current codebase:

| Feature ID | Proposed Capability | Architectural Motivation & Prerequisite |
| :--- | :--- | :--- |
| **PFR-01** | **Private Repository Support** | Requires storing user-delegated GitHub OAuth access tokens with `repo` scope, encrypted at rest via AES-GCM, and passing them to Git clone operations. |
| **PFR-02** | **Symbol-Level Call Graphs** | Requires cross-file symbol resolution and type-inference indexing (LSP or SCIP indexing), expanding edges from file-to-file to function-to-function. |
| **PFR-03** | **Webhook-Triggered Incremental Analysis** | Requires GitHub Webhook ingestion (`push` events) and git diff-based partial re-parsing, persisting only modified files rather than wiping the entire repo. |
| **PFR-04** | **Distributed Rate Limiting** | Requires replacing the current in-memory sliding window middleware with a Redis-backed token bucket algorithm shared across multiple API replicas. |
| **PFR-05** | **Multi-Tenant Quotas & Billing** | Requires tenant organization models, monthly analysis credit tracking, and Stripe webhook integration. |
| **PFR-06** | **Managed Vector Database Cluster** | Replacing single-node containerized ChromaDB with managed Qdrant or PostgreSQL `pgvector` to support horizontal vector search scaling. |
| **PFR-07** | **LLM Provider Fallback Router** | Automated circuit-breaker switching from Groq cloud to secondary cloud providers (e.g. Anthropic/OpenAI) or local Ollama on 429 rate limit errors. |
| **PFR-08** | **Interactive Code Editing & PR Creation** | AI-assisted code refactoring that writes changes directly to a new GitHub pull request. |
