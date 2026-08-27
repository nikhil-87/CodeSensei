# 16. Scalability Bottleneck Analysis & Ranking

> **Status:** Codebase-grounded evaluation of capacity ceilings, resource saturation, and breaking points.  
> **Source Verification:** [worker/worker/app/tasks/analyze_repository.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/tasks/analyze_repository.py), [backend/app/core/middleware.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/middleware.py), [docker/docker-compose.free-tier.yml](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/docker/docker-compose.free-tier.yml).

---

## 1. System Bottleneck Ranking

When load scales from hundreds to millions of requests, components break in a predictable order based on resource constraints, network I/O, and transaction locks:

```
┌────────────────────────────────────────────────────────────────────────┐
│                      BREAKS 1ST: Worker Disk I/O & Git Clone Time      │
│  Symptom: Queue backlog explodes; worker disk fills up; clone timeouts │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   BREAKS 2ND: Third-Party LLM & Embedding Rate Limits  │
│  Symptom: 429 Too Many Requests; degraded AI answers; vector drops     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   BREAKS 3RD: ChromaDB Single-Node Memory Exhaustion   │
│  Symptom: Chroma OOM kills; vector query latency degrades >1000ms      │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   BREAKS 4TH: PostgreSQL Batch Write Lock Contention   │
│  Symptom: Connection pool exhaustion during atomic wipe-and-replace    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   BREAKS 5TH: In-Memory Rate Limiting Inconsistency    │
│  Symptom: Leaky limits across API pods; noisy neighbor abuse           │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 1.1 Breaks FIRST: Background Worker Disk I/O & Git Clone Operations
- **Why it breaks first:** Git shallow cloning is network-bound on GitHub and disk-I/O bound on the host filesystem. A 100MB repository clone takes 15–45 seconds. With a single worker process (or even 2–4 workers), receiving 50 concurrent repository submissions creates an immediate 20-minute queue backlog. Furthermore, if workers share a single disk volume (`/var/lib/codesensei/workspaces`), concurrent clones saturate disk write IOPS, causing timeouts and reaper failures.
- **Evidence in Code:** `GitCloner.clone` writes to local disk with a hard 120s timeout (`CLONE_TIMEOUT_SECONDS=120`).

### 1.2 Breaks SECOND: External AI Rate Limits (Groq & HuggingFace Free Tiers)
- **Why it breaks second:** Groq's free cloud tier enforces a strict limit of **30 requests per minute**. If 10 concurrent users actively chat with the AI assistant, or if 5 workers simultaneously request batch embeddings from HuggingFace, the third-party APIs return HTTP 429 (Rate Limit Exceeded).
- **Evidence in Code:** `providers.py` explicitly documents `"rate_limit": "30 requests/minute"` on Groq. While `AIService` catches errors and emits an SSE error event, the feature becomes unusable for clients under modest concurrency.

### 1.3 Breaks THIRD: ChromaDB Single-Node Memory Saturation
- **Why it breaks third:** In the current deployment (`docker-compose.free-tier.yml`), ChromaDB runs inside a single container limited to 512MB RAM. Chroma holds in-memory HNSW index structures for every collection (`repo_<id>`). When 500+ repositories are indexed, each containing 500–2,000 chunk vectors, ChromaDB exhausts container memory, triggers an OOM kill, and crashes.
- **Evidence in Code:** `docker-compose.free-tier.yml` specifies `resources.limits.memory: 512M` for `chroma`.

### 1.4 Breaks FOURTH: PostgreSQL Batch Write Locks During Re-Analysis
- **Why it breaks fourth:** When a worker persists an analysis run, it executes:
  ```python
  DELETE FROM source_files WHERE repository_id = :id
  ```
  PostgreSQL cascades this delete across foreign keys to delete thousands of rows in `symbols`, `dependencies`, and `metrics`. This acquires exclusive row and table locks on these tables. If multiple workers persist analyses simultaneously, lock contention spikes database CPU, causing transaction pool timeouts on the API.

### 1.5 Breaks FIFTH: In-Memory Rate Limiter Drift Across Horizontally Scaled APIs
- **Why it breaks fifth:** The current `RateLimitMiddleware` maintains an in-memory dictionary (`self._requests[client_ip]`). When the backend scales from 1 API process to 10 Kubernetes pods, the rate limit is fragmented: an attacker allowed 60 req/min can issue 600 req/min (60 to each of the 10 pods) because memory is not shared across processes.

---

## 2. Comprehensive Component Bottleneck Analysis

| Component | Current Bottleneck | Underlying Cause | Current Mitigation in Code | Long-Term Scaling Strategy | Trade-off of Strategy |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Worker / Cloning** | Disk I/O & Network latency | Shallow Git cloning requires writing entire repo trees to local filesystem. | `depth=1` shallow clone; 100MB size limit; 120s timeout. | Ephemeral NVMe scratch storage; Git packfile in-memory streaming; pre-flight GitHub API size check. | Increased cloud infrastructure cost for NVMe instances. |
| **Worker / Queue** | Head-of-line blocking | A single large repo (90MB) blocks dozens of small repos (500KB) in the queue. | `SimpleWorker` burst polling loop. | Partition queue into `queue:small`, `queue:medium`, `queue:large` with dedicated worker pools. | More worker processes to manage and monitor; potential idle capacity on large queues. |
| **Analysis Engine** | AST parsing CPU saturation | Parsing thousands of files across complex grammars consumes 100% CPU on worker. | `ThreadPoolExecutor` with `parse_workers=4` across files. | Compile Tree-sitter parsers to optimized Rust/C binaries; distribute parsing jobs across worker nodes. | Native C-dependencies increase build and cross-platform compilation complexity. |
| **Vector DB (ChromaDB)**| Single-node memory limit | In-memory HNSW index structures scale linearly with vector count; 512MB RAM cap. | `_try_index` catches errors (`IndexingDegraded`); collection deletion on repo delete. | Migrate to distributed vector database cluster (Qdrant or pgvector on Aurora) with disk-backed storage. | Network latency overhead for vector queries compared to co-located Chroma. |
| **LLM Provider (Groq)** | 30 requests/min rate limit | Free-tier cloud API quotas restrict concurrent multi-user chat sessions. | SSE error handling with clean termination. | Multi-provider fallback router (Groq -> Anthropic -> OpenAI) or self-hosted vLLM GPU pool. | API token costs for paid tier providers; GPU server operational costs. |
| **Relational Database** | Cascade delete lock contention | `DELETE FROM source_files` locks thousands of dependent rows during re-analysis. | Bulk batch insertions via SQLAlchemy Core; single atomic transaction. | Soft deletes with asynchronous background purge; table partitioning by `repository_id`. | Storage overhead for soft-deleted rows until async vacuum/purge runs. |
| **API Rate Limiter** | Process-local memory isolation | Each API replica maintains an independent sliding window dictionary. | `X-Forwarded-For` and `X-Real-IP` header resolution. | Redis-backed distributed token bucket algorithm (e.g. `redis-py` sliding window script). | Adds a Redis network roundtrip (~1ms) to every incoming HTTP request. |
| **Graph Algorithm** | Tarjan's SCC CPU cost on large graphs | Graphs with >5,000 files and >50,000 edges increase cycle detection latency. | Responses cached in Redis (`repo:<id>:graph`, TTL: 3600s). | Pre-calculate cycle groups in worker during analysis and store directly in DB schema. | Increases worker persistence time and database schema complexity. |
| **Database Connections**| Connection pool exhaustion | Default `pool_size=5` (free tier) exhausted under concurrent API requests. | Dual-Transaction pattern drops DB connection during LLM streaming. | PgBouncer connection pooler sitting in front of PostgreSQL. | PgBouncer requires operational tuning and disables prepared statements in transaction mode. |
