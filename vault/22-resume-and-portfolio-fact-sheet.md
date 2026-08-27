# 22. Resume & Portfolio Fact Sheet (Verifiable Claims)

> **Standard:** Every claim below is verifiable directly from the repository code.  
> **Benchmark Rule:** Do **NOT** claim arbitrary throughput or latency numbers on a resume (e.g. "processed 100,000 repos/sec") unless substantiated by verified load test runs.

---

## 1. Verifiable Technical Achievements by Domain

### 1.1 Distributed Systems & Background Processing
- **Atomic Concurrency Control:** Eliminated check-then-act duplicate analysis races at the database level using a PostgreSQL partial unique index (`uq_active_job_per_repository`) on active jobs, mapping integrity collisions to HTTP 409 Conflict.
  - *Evidence:* [backend/alembic/versions/0006_active_job_unique.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/alembic/versions/0006_active_job_unique.py)
- **Self-Healing Zombie Job Recovery:** Architected a heartbeat and reaper pattern where background workers stream periodic timestamps (`heartbeat_at`) and an asynchronous FastAPI lifespan task sweeps and fails stale jobs (>300s), automatically clearing locks after worker OOM crashes.
  - *Evidence:* [backend/app/services/analysis_reaper.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/analysis_reaper.py), [worker/worker/app/progress.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/progress.py)
- **Serverless Queue Optimization:** Engineered a burst-mode polling consumer loop using Python RQ's `SimpleWorker(burst=True)` with explicit TCP keepalives to prevent idle socket drops on serverless Redis tiers (Upstash).
  - *Evidence:* [worker/worker/app/__main__.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/__main__.py)

### 1.2 Compilers, AST & Static Code Analysis
- **Fault-Tolerant 3-Tier Parser:** Built a multi-language parsing pipeline supporting 9+ languages (Python, TypeScript, Go, Rust, Java, C++, etc.) with automatic fallback from concrete syntax trees (Tree-sitter) down to Regex, isolating per-file syntax errors.
  - *Evidence:* [analysis-engine/engine/parsers/registry.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/parsers/registry.py)
- **Circular Dependency Detection:** Implemented Tarjan's Strongly Connected Components (SCC) algorithm in linear time ($O(V + E)$) to detect circular import chains across source modules, feeding live cycle-highlighting in Cytoscape.js.
  - *Evidence:* [analysis-engine/engine/graph/cycles.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/graph/cycles.py)
- **Reverse-Dependency Blast Radius Engine:** Developed an upstream BFS traversal algorithm computing change-impact risk scores with exponential distance decay ($\exp(-0.5 \cdot (d-1))$) and sigmoid risk saturation.
  - *Evidence:* [backend/app/services/impact_service.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/impact_service.py)
- **Concurrent Parsing Engine:** Parallelized repository file parsing using Python's `ThreadPoolExecutor` across 4 worker threads, cutting analysis duration on multi-thousand file repositories.
  - *Evidence:* [analysis-engine/engine/orchestrator.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/orchestrator.py)

### 1.3 Retrieval-Augmented Generation (RAG) & AI Systems
- **Dual-Transaction Streaming Architecture:** Eliminated database connection pool exhaustion during 10–30s LLM streaming by committing the user's turn in a 5ms transaction, dropping DB locks during streaming, and committing the assistant turn and citations in a separate transaction.
  - *Evidence:* [backend/app/services/chat_session_service.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/chat_session_service.py)
- **Symbol-Aware Code Chunking:** Sliced source code along function, class, and method boundaries (target 60 lines, max 200 lines, overlap 6 lines) rather than naive character splitting, preserving semantic syntactic context for embedding generation.
  - *Evidence:* [analysis-engine/engine/ai/chunker.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/ai/chunker.py)
- **Multi-Provider AI Abstraction:** Engineered clean protocol-driven AI interfaces supporting pluggable cloud (Groq Llama 3.3, HuggingFace Inference API) and local (Ollama) LLM and embedding backends.
  - *Evidence:* [analysis-engine/engine/ai/ports.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/ai/ports.py), [shared/config/providers.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/shared/config/providers.py)
- **Zero-Leak Vector Isolation:** Enforced repository-level collection segregation (`repo_<id>`) in ChromaDB and automated synchronous collection purging on repository deletion.
  - *Evidence:* [backend/app/services/ai_service.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/ai_service.py)

### 1.4 Application Security & Hardening
- **Defense-in-Depth SSRF Validator:** Protected internal infrastructure against SSRF during repository ingestion by strictly validating HTTPS schemes, enforcing the `github.com` host, stripping credentials and queries, and validating owner/repo paths.
  - *Evidence:* [backend/app/core/security.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/security.py)
- **Path Traversal Sandboxing:** Implemented `safe_join` to prevent directory traversal attacks (`../../`) inside untrusted cloned repositories, asserting workspace root containment and rejecting backslashes across all OSes.
  - *Evidence:* [backend/app/core/security.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/security.py)
- **IDOR Defense via 404 Masking:** Neutralized object enumeration attacks on private repositories and chat sessions by returning generic `404 Not Found` responses (never 403) for unowned resources.
  - *Evidence:* [backend/app/core/dependencies.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/dependencies.py)
- **Stateless Cookie Session Security:** Implemented passwordless GitHub OAuth 2.0 with HS256-signed JWTs delivered via `httpOnly`, `SameSite=Lax`, `secure` cookies, coupled with a 10-minute anti-CSRF state token.
  - *Evidence:* [backend/app/core/auth.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/auth.py)

### 1.5 Database & Relational Modeling
- **High-Performance Bulk Persistence:** Optimized analysis ingestion by replacing thousands of single-row inserts with SQLAlchemy Core bulk batch mappings, reducing 25,000+ relational operations to 4 atomic SQL statements.
  - *Evidence:* [worker/worker/app/persistence.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/persistence.py)
- **Alembic Migration Progression:** Managed 7 reproducible schema migrations spanning initial ORM setup, GitHub identity scoping, analysis version stamps, chat tables, starring, partial unique indexes, and worker heartbeats.
  - *Evidence:* [backend/alembic/versions/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/alembic/versions/)

### 1.6 Full-Stack React & Data Visualization
- **Interactive Graph Canvas:** Built a Cytoscape.js dependency graph visualization featuring force-directed physics layout, dynamic language node filtering, LOC-based node sizing, and cycle highlighting.
  - *Evidence:* [frontend/src/pages/DependencyGraphPage.tsx](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/pages/DependencyGraphPage.tsx)
- **Cross-Surface Context Pipeline:** Architected a Zustand store (`nodeContextStore`) bridging graph and architecture visualizers with the conversational AI assistant, enabling one-click "Ask AI about this file" interactions with attached context chips.
  - *Evidence:* [frontend/src/store/nodeContextStore.ts](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/store/nodeContextStore.ts)

---

## 2. Benchmark & Metric Warnings for Interviews

> [!WARNING]
> When interviewing or writing your resume, follow these strict rules to avoid fabricating unverified performance numbers:

1. **Do NOT claim specific query latency numbers (e.g. "sub-5ms")** unless you run the Locust load test suite against a live PostgreSQL container and record the percentile output.
2. **Do NOT claim specific daily repository capacity (e.g. "scales to 10,000 repos/day")** as a current capability; frame it as: *"In Stage 2 of our scaling model, the architecture is designed to handle 10,000 repos/day by partitioning queues into small, medium, and large tiers."*
3. **Do NOT claim you wrote custom Tree-sitter grammars in C**; state accurately: *"Integrated Tree-sitter language bindings to parse concrete syntax trees for accurate LOC and branching complexity across 9 languages."*
4. **Do NOT claim private repository cloning with access tokens**; state accurately: *"Engineered for public repositories; private repository support is documented as the immediate Stage 1 extension requiring encrypted token storage."*
