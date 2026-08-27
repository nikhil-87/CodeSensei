# 03. Non-Functional Requirements — Grounded Implementation vs. Scale Evolution

> **Status:** Codebase-grounded analysis of current properties vs. architectural targets.  
> **Source Verification:** [backend/app/core/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/), [docker/docker-compose.free-tier.yml](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/docker/docker-compose.free-tier.yml), [backend/app/services/analysis_reaper.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/analysis_reaper.py).

---

## 1. Grounded NFR Architecture Matrix

| Dimension | Current Implementation (Stage 0) | Scale Target (Stages 1–3) |
| :--- | :--- | :--- |
| **Security** | Stateless JWT in `httpOnly` cookie; SSRF URL validator; `safe_join` path traversal guard; IDOR 404 masking; Swagger disabled in prod. | WAF edge inspection (Cloudflare); mTLS between microservices; HashiCorp Vault secrets management; KMS envelope encryption. |
| **Reliability** | Atomic DB transactions for persistence; worker heartbeat with reaper auto-recovery; partial unique index preventing duplicate runs. | At-least-once queue semantics with dead-letter queue (DLQ); multi-region worker pools; circuit breakers on external AI APIs. |
| **Availability** | Single-instance API & Worker (in free-tier compose) with container healthchecks (`/healthz`, `/readyz`). | Multi-AZ stateless API pods behind Load Balancer; auto-scaling worker groups; PostgreSQL primary-replica failover. |
| **Performance** | Redis caching on heavy graph/dead-code reads; parallel parsing via ThreadPoolExecutor (`parse_workers=4`); SSE streaming. | Redis Cluster token-bucket cache; pgvector indexed HNSW search; worker read-replicas; asynchronous vector batching. |
| **Scalability** | Single RQ queue on Redis; horizontal worker replicas supported via `WORKER_REPLICAS` setting; DB connection pooling. | Dynamic K8s HPA based on queue depth (`worker_concurrency`); partition queues by repo size; distributed DB sharding. |
| **Maintainability** | Decoupled `analysis-engine` (zero web dependencies); modular FastAPI routers; Alembic migrations with naming conventions. | Microservice boundaries for engine extraction; OpenAPI client generation; automated contract testing in CI. |
| **Observability** | Structlog JSON logging with bound `request_id`; Prometheus metrics middleware (:9100 / `/metrics`); `/healthz` & `/readyz`. | Distributed tracing via OpenTelemetry / Jaeger; centralized Grafana Cloud alerting; Sentry error aggregation. |
| **Data Consistency**| PostgreSQL ACID transactions; Foreign key `ON DELETE CASCADE` across all entities; denormalized counters kept in sync via services. | Eventual consistency via transactional outbox pattern on Kafka; distributed consensus for cross-region data stores. |
| **Fault Tolerance** | Best-effort Chroma vector indexing (degradation does not fail job); defensive parser exception handlers; Upstash burst worker. | Automated worker checkpointing on large git clones; retry backoff with jitter; multi-provider LLM failover. |
| **Resource Limits** | Default 100MB repo size limit; 10,000 files max; 1MB max file size; 120s clone timeout; Docker container memory caps (512MB–1GB). | Dynamic per-tenant storage quotas; tiered concurrency queues; ephemeral spot instances with automatic preemption handlers. |
| **Privacy** | Public GitHub repos only (no credentials stored); Chroma collection purged on repo deletion; private repo chat sessions masked. | SOC2 compliance; GDPR data retention policies; private repository customer-managed key encryption (BYOK). |
| **Cost** | 100% free-tier compatible: Neon PG free tier, Upstash Redis free tier, Groq free API, HuggingFace Inference API, Oracle Cloud Free Tier. | Optimized reserved compute instances; spot instances for background workers; cached vector embeddings to minimize model API fees. |

---

## 2. Detailed Dimension Breakdown

### 2.1 Security
- **Current Implementation:**
  - Authentication tokens are minted as signed HS256 JWTs and delivered via an `httpOnly`, `SameSite=Lax`, `secure` (in production) cookie (`codesensei_session`). Tokens expire in 7 days.
  - Cross-Site Request Forgery (CSRF) in OAuth is mitigated via a short-lived (10-minute) `codesensei_oauth_state` cookie checked on callback.
  - Server-Side Request Forgery (SSRF) is strictly blocked by `validate_github_url`: enforces `https://`, host `github.com`, no credentials, no query parameters, and regex matching.
  - Path traversal is prevented by `safe_join`: enforces that candidate paths resolve strictly within the workspace directory and outright rejects backslashes (`\`).
  - Insecure Direct Object References (IDOR) are mitigated in `verify_repository_access`: private repositories or unowned resources return `404 Not Found` rather than `403 Forbidden` to prevent resource enumeration.
  - Production gating: Interactive documentation (`/docs`, `/redoc`, `/openapi.json`) and developer bypasses (`/api/v1/auth/dev-login`) are disabled when `APP_ENV=production`.
- **Evolution at Scale:**
  - Transition from HS256 symmetric signing to RS256 asymmetric keys with a JWKS endpoint to decouple auth token verification across multiple independent microservices.
  - Deploy edge WAF rules (Cloudflare) to filter common web vulnerabilities before requests hit application containers.

### 2.2 Reliability & Fault Tolerance
- **Current Implementation:**
  - Background analysis jobs update a `heartbeat_at` timestamp. If a worker crashes mid-run (OOM or VM restart), the backend reaper task identifies stale jobs (>300s since heartbeat) and transitions them to `FAILED`, resetting the active-job lock.
  - At most one active job (`queued` or `running`) can exist per repository, enforced by the PostgreSQL partial unique index `uq_active_job_per_repository`. This prevents race conditions from spawning duplicate clone and analysis operations.
  - Vector indexing in ChromaDB is treated as **best-effort**: if ChromaDB is unavailable or throws `IndexingDegraded`, the static analysis still commits successfully, marking the repository `READY` so users can explore code graphs even if AI search is degraded.
  - Parser registry applies defensive exception handling: a syntax error in an individual file is caught, falling back to regex parsing; if regex fails, the file returns empty metrics rather than terminating the whole repository run.
- **Evolution at Scale:**
  - Implement Redis Queue Dead Letter Queues (DLQ) with exponential backoff retries and alert notifications on three consecutive failures.
  - Introduce worker checkpointing during Git cloning so large repositories interrupted by preemption can resume without re-downloading git objects.

### 2.3 Performance & Resource Limits
- **Current Implementation:**
  - Concurrent parsing: `AnalysisOrchestrator._parse_all` uses a `ThreadPoolExecutor` with `parse_workers=4` to parse multiple files in parallel.
  - Multi-tier caching: Heavy query results for Dependency Graphs, Dead Code Reports, and Architecture Maps are cached in Redis as JSON with a configurable TTL (default 3,600s).
  - Memory bounds:
    - Repository size capped at `API_MAX_REPO_SIZE_MB=100` MB.
    - File count capped at `API_MAX_REPO_FILES=10,000` files.
    - Single file size capped at `API_MAX_FILE_BYTES=1,048,576` bytes (1MB).
    - Git clone timeout capped at `CLONE_TIMEOUT_SECONDS=120` seconds.
  - Container limits (in `docker-compose.free-tier.yml`):
    - Backend: 512MB RAM limit, 0.5 CPU limit.
    - Worker: 1024MB RAM limit, 1.0 CPU limit.
    - Chroma: 512MB RAM limit.
    - Frontend: 128MB RAM limit.
- **Evolution at Scale:**
  - Move from local filesystem cloning to ephemeral NVMe scratch disks or memory-backed RAM disks for git operations.
  - Scale vector search from ChromaDB to an external managed pgvector or Qdrant cluster with HNSW indexing to support sub-50ms vector queries across millions of code chunks.

### 2.4 Data Consistency & Transactions
- **Current Implementation:**
  - Relational consistency: PostgreSQL enforces relational integrity via Foreign Keys with `ON DELETE CASCADE`. Deleting a repository cascades cleanly across `source_files`, `symbols`, `dependencies`, `metrics`, `analysis_jobs`, `stars`, and `chat_sessions`.
  - Persistence atomicity: When a worker persists an analysis run, it deletes all existing `SourceFile` records for the repository and re-inserts new records within a single database transaction, ensuring no intermediate partial state is visible.
  - Streaming transaction isolation: In `ChatSessionService.stream_chat`, the system explicitly avoids keeping a long-lived database transaction open during a multi-second LLM stream. It opens Transaction 1 to save the user turn, streams tokens, and opens Transaction 2 to save the assistant turn.
  - Denormalized counters: `repositories.star_count`, `file_count`, and `total_lines` are maintained directly by the service layer to avoid expensive runtime `COUNT(*)` queries on list pages.
- **Evolution at Scale:**
  - Introduce an asynchronous transaction log or Event Sourcing for repository mutations to support read-replica distribution with zero replication lag impact.

### 2.5 Observability
- **Current Implementation:**
  - Structured logging: Configured via `structlog`, outputting structured JSON logs. Every request is assigned a unique `X-Request-ID` UUID passed through headers and bound to log contexts.
  - Prometheus metrics: Exposed via `/metrics` on the API, tracking request counts (`http_requests_total`), request duration histograms (`http_request_duration_seconds`), enqueued jobs (`analysis_jobs_enqueued_total`), and AI chat completions (`ai_chat_requests_total`).
  - Worker metrics: Exposed on port :9100 tracking job outcomes, files processed, and chunks indexed.
  - Health checks: `/healthz` provides liveness; `/readyz` executes deep dependency probes testing live reachability of PostgreSQL (`SELECT 1`) and Redis (`ping`).
- **Evolution at Scale:**
  - Instrument OpenTelemetry distributed tracing across HTTP requests, Redis queue delay, worker execution, and external AI calls.
  - Configure automated PagerDuty / Opsgenie alert thresholds on worker queue depth, failed job ratios, and 5xx error spikes.

### 2.6 Cost Considerations
- **Current Implementation:**
  - Designed specifically to operate at **$0/month infrastructure cost**:
    - **PostgreSQL:** Neon Serverless free tier (0.5 GB storage, auto-suspend).
    - **Redis:** Upstash Serverless free tier (10,000 commands/day, TLS).
    - **LLM:** Groq Cloud API free tier (30 requests/minute on Llama 3.3 70B).
    - **Embeddings:** HuggingFace Serverless Inference API free tier (`all-MiniLM-L6-v2`).
    - **Compute:** Single 1–4GB RAM VM (Oracle Cloud Always Free Ampere A1 instance or local machine).
- **Evolution at Scale:**
  - Provision auto-scaling compute pools using AWS ECS Fargate or EKS with Spot Instances for workers to minimize processing costs for spiky workloads.
  - Cache common code embeddings globally to eliminate duplicate embedding API costs across public repositories.
