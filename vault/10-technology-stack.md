# 10. Technology Stack Inventory & Trade-Off Analysis

> **Status:** Codebase-grounded inventory based on active dependencies and package configurations.  
> **Source Verification:** [backend/pyproject.toml](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/pyproject.toml), [worker/pyproject.toml](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/pyproject.toml), [analysis-engine/pyproject.toml](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/pyproject.toml), [frontend/package.json](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/package.json).

---

## 1. Complete Technology Inventory

| Layer | Technology | Version | Purpose in CodeSensei |
| :--- | :--- | :--- | :--- |
| **API Framework** | **FastAPI** | `~0.115.0` | Asynchronous REST and SSE endpoints, request validation, dependency injection. |
| **ASGI Server** | **Uvicorn** | `~0.30.0` | High-performance asynchronous HTTP server for FastAPI. |
| **ORM / Data Access** | **SQLAlchemy** | `~2.0.35` | Typed asynchronous data layer (`asyncpg`) and migration modeling. |
| **Database Migrations** | **Alembic** | `~1.14.0` | Version-controlled, reproducible database schema migrations. |
| **Relational Database** | **PostgreSQL** | `16` | System of record for repositories, files, symbols, metrics, and chat history. |
| **Task Queue & Cache** | **Redis** | `7` | Background job queuing (RQ) and sub-millisecond response caching. |
| **Task Runner** | **RQ (Redis Queue)** | `~2.0.0` | Lightweight background worker process driving repository analysis. |
| **Vector Database** | **ChromaDB** | `0.5.5` | Storage and cosine similarity search for code chunk embeddings. |
| **Static Code Parsing** | **tree-sitter** | `~0.23.0` | Multi-language concrete syntax tree parser for accurate LOC/branch counts. |
| **Cloud LLM Provider** | **Groq API** | Cloud | Ultra-low latency Llama-3.3-70b-versatile token generation on free tier. |
| **Local LLM Provider** | **Ollama** | Latest | Self-contained local container fallback for chat and embedding generation. |
| **Embedding Provider** | **HuggingFace API** | Cloud | Free serverless vector generation (`all-MiniLM-L6-v2`, 384 dimensions). |
| **Frontend Framework** | **React** | `^18.3.1` | Declarative component hierarchy and virtual DOM rendering. |
| **Build Tool** | **Vite** | `^5.4.2` | Fast ESM development server and optimized production bundler. |
| **Graph Visualization**| **Cytoscape.js** | `^3.30.2` | Graph theory canvas for interactive dependency graph navigation. |
| **Client State** | **Zustand** | `^5.0.0` | Lightweight state management for cross-surface node context sharing. |
| **Server State Cache** | **TanStack Query** | `^5.56.2` | Client-side query caching, deduplication, and background refetching. |
| **Styling** | **TailwindCSS** | `^3.4.11` | Utility-first responsive design and curated dark-mode theme. |
| **Web Server (Ingress)**| **Nginx** | `1.27-alpine` | Non-root reverse proxy forwarding `/api/v1` to FastAPI and serving SPA. |
| **Observability** | **Prometheus + structlog**| Latest | Standard Prometheus metrics exposition and structured JSON logging. |

---

## 2. Deep-Dive Architectural Trade-Off Analysis

### 2.1 Backend Framework: FastAPI vs. Django vs. Flask

- **Chosen:** **FastAPI**
  - **Why it is used:** CodeSensei requires native async I/O to handle long-lived Server-Sent Events (SSE) connections for real-time analysis progress and token streaming. FastAPI's Pydantic v2 integration provides automatic schema validation and serialization.
  - **Trade-offs:** FastAPI is less "batteries-included" than Django; it does not ship with built-in admin dashboards, authentication models, or session backends, requiring us to assemble these primitives cleanly via dependencies.
  - **Alternatives Considered:**
    - *Django / Django Ninja:* Django's synchronous ORM history and heavier WSGI footprint add unnecessary overhead. While Django Ninja provides Pydantic support, Django's monolithic nature is mismatched with our decoupled analysis engine.
    - *Flask:* Lacks native async concurrency, requiring Gevent or Quart workarounds for SSE streaming, and lacks built-in request schema validation.

---

### 2.2 Relational Store: PostgreSQL vs. MongoDB / Document Stores

- **Chosen:** **PostgreSQL 16**
  - **Why it is used:** CodeSensei's domain model is inherently relational. Files declare symbols; symbols link to files; files have directed dependency edges to other files; users own repositories; chat sessions own messages. PostgreSQL enforces referential integrity (`ON DELETE CASCADE`) and transactional atomicity.
  - **Critical Code-Grounded Decider:** Alembic migration `0006_active_job_unique.py` leverages PostgreSQL's **partial unique index** (`WHERE status IN ('queued', 'running')`) to eliminate check-then-act duplicate analysis races at the database level. Document databases lack equivalent partial uniqueness constraints without complex distributed locking.
  - **Trade-offs:** Requires explicit schema migrations via Alembic. Wiping and re-inserting thousands of file records on re-analysis requires batching to avoid write locks.
  - **Alternatives Considered:**
    - *MongoDB:* While JSON-like documents fit raw analysis results, querying relational reverse-dependencies (impact analysis) or circular import chains requires expensive `$graphLookup` aggregation pipelines that degrade rapidly compared to PostgreSQL indexed foreign keys.

---

### 2.3 Background Processing: Redis Queue (RQ) vs. Celery vs. Kafka

- **Chosen:** **RQ (Redis Queue)**
  - **Why it is used:** RQ provides a lightweight, pure-Python background worker architecture on top of Redis. The backend enqueues jobs by string (`ANALYZE_REPOSITORY_JOB = "worker.app.tasks.analyze_repository.run"`), decoupling the API process from worker imports.
  - **Critical Code-Grounded Decider:** In `worker/worker/app/__main__.py`, we run `SimpleWorker` in **burst mode** (`worker.work(burst=True)`). This allows the worker to process available jobs and close its connection, preventing connection timeouts on serverless Redis tiers (Upstash) which terminate idle persistent connections.
  - **Trade-offs:** RQ lacks complex workflow DAG orchestration (like Celery canvases) and does not support sub-millisecond event streaming. For single-job repository analyses, its simplicity outweighs these limitations.
  - **Alternatives Considered:**
    - *Celery:* Highly complex configuration, heavy broker requirements, and notoriously difficult connection recovery on serverless Redis.
    - *Apache Kafka:* Unjustified operational complexity for a discrete task queue where message ordering across different repositories is unnecessary.

---

### 2.4 Vector Database: ChromaDB vs. pgvector vs. Qdrant

- **Chosen:** **ChromaDB 0.5.5**
  - **Why it is used:** ChromaDB runs as a lightweight, zero-configuration standalone vector database. It supports collection partitioning out of the box, allowing CodeSensei to isolate each repository's code chunks into a dedicated collection (`repo_<repository_id>`).
  - **Trade-offs:** ChromaDB 0.5.5 in a single container stores indices in memory and local SQLite files, creating a vertical scaling ceiling.
  - **Alternatives Considered:**
    - *PostgreSQL pgvector:* Attractive for consolidating all data into Postgres. However, in free-tier cloud environments (e.g. Neon), vector indexes consume high memory and compute against tight database quotas. Decoupling vector search into Chroma protects PostgreSQL performance.
    - *Managed Qdrant / Pinecone:* Excellent scaling, but introduces external cloud dependencies and potential service costs outside the zero-dollar free-tier constraint.

---

### 2.5 Code Parsing Strategy: 3-Tier Registry vs. Language Server Protocol (LSP)

- **Chosen:** **3-Tier Registry (Python AST + Tree-sitter + Regex Fallback)**
  - **Why it is used:** Analyzing arbitrary repositories across 9+ programming languages in a lightweight container requires fault-tolerant parsing that does not require downloading full language runtimes (Go compilers, Rust cargo, JDKs).
  - **How it Works in Code ([parsers/registry.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/parsers/registry.py)):**
    1. *Python native AST:* Full semantic symbol and import extraction.
    2. *Tree-sitter:* Parses concrete syntax trees to count executable LOC and branch complexity without being tripped by comments or multi-line template literals.
    3. *Regex Parser:* Fast pattern matching for declarations and imports across languages when Tree-sitter grammars are uninstalled.
  - **Trade-offs:** Regex and Tree-sitter extract *file-level* imports and declarations, but cannot perform deep cross-file type resolution (e.g., resolving `foo.bar()` when `foo` is imported from an external third-party library).
  - **Alternatives Considered:**
    - *LSP (Language Server Protocol) Daemons:* Installing and spinning up language servers (e.g., `gopls`, `rust-analyzer`, `typescript-language-server`) requires massive container images (10GB+), high RAM, and minutes of dependency downloading per repository clone, rendering zero-cost multi-language analysis impossible.

---

### 2.6 Graph Visualization: Cytoscape.js vs. D3.js vs. React Flow

- **Chosen:** **Cytoscape.js**
  - **Why it is used:** CodeSensei needs a graph-theory canvas that can render hundreds of nodes and directed edges with automated force-directed physics layout (`cose`). Cytoscape includes built-in graph algorithms and optimized Canvas rendering.
  - **Trade-offs:** Canvas-based rendering makes custom HTML styling of nodes more complex than SVG-based tools.
  - **Alternatives Considered:**
    - *React Flow:* Ideal for workflow builders with custom node UIs, but performs poorly with large automated graph layouts (>500 nodes) and lacks native graph-theory algorithms.
    - *D3.js:* Extreme flexibility, but requires writing force simulations, zoom/pan handlers, and node hitboxes from scratch.

---

### 2.7 Frontend State: Zustand + React Query vs. Redux Toolkit

- **Chosen:** **Zustand + TanStack Query (React Query)**
  - **Why it is used:** Clean separation of concerns:
    - *TanStack Query:* Handles all server-state caching, pagination, deduplication, and refetching.
    - *Zustand:* Handles cross-surface UI state (`useNodeContextStore`) with minimal boilerplate (<70 lines of code) and zero context provider re-rendering overhead.
  - **Trade-offs:** Requires discipline to prevent developers from duplicating server data in local Zustand stores.
  - **Alternatives Considered:**
    - *Redux Toolkit:* Excessive boilerplate, actions, and reducers for an application where 90% of state is asynchronous server data.
