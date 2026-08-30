# PROJECT_SOURCE_OF_TRUTH.md: CodeSensei Platform

> **Authoritative Technical Reference & Architecture Ground Truth**  
> **Document Purpose:** Single source of truth for the codebase as of August 2026. Designed for deep engineering audits, senior/staff technical interview preparation, and extraction of resume-grade technical accomplishments.  
> **Ground Truth Rule:** Every entity, route, algorithm, failure mode, and architectural trade-off documented here is directly derived from active repository code. Hypothetical extensions and scaling roadmaps are strictly isolated and labeled `[PROPOSED / SCALING OPTION]`.

---

# Table of Contents
1. [Project Overview](#1-project-overview)
2. [Current Feature Inventory](#2-current-feature-inventory)
3. [System Architecture & Current-State Topology](#3-system-architecture--current-state-topology)
4. [End-to-End User Flows & Sequence Traces](#4-end-to-end-user-flows--sequence-traces)
5. [Core Execution & Asynchronous Processing Engine](#5-core-execution--asynchronous-processing-engine)
6. [Data Model & Relational Database Schema](#6-data-model--relational-database-schema)
7. [Comprehensive API Reference](#7-comprehensive-api-reference)
8. [Authentication, Authorization & Session Management](#8-authentication-authorization--session-management)
9. [Application Security & Hardening Realities](#9-application-security--hardening-realities)
10. [Error Handling, Failure Scenarios & Reliability](#10-error-handling-failure-scenarios--reliability)
11. [Frontend Architecture & State Topology](#11-frontend-architecture--state-topology)
12. [Backend Architecture & Service Boundaries](#12-backend-architecture--service-boundaries)
13. [Technology Stack & Architectural Alternatives](#13-technology-stack--architectural-alternatives)
14. [Engineering Decisions & Trade-Off Matrix](#14-engineering-decisions--trade-off-matrix)
15. [Scaling the System (Stages 1 through 3)](#15-scaling-the-system-stages-1-through-3)
16. [Bottlenecks & Critical Breaking Points](#16-bottlenecks--critical-breaking-points)
17. [Comprehensive Edge-Case Inventory](#17-comprehensive-edge-case-inventory)
18. [Testing Architecture & Verification Reality](#18-testing-architecture--verification-reality)
19. [Observability, Telemetry & Operations](#19-observability-telemetry--operations)
20. [Deployment & Infrastructure Topology](#20-deployment--infrastructure-topology)
21. [Verified Current Technical Limitations](#21-verified-current-technical-limitations)
22. [Future Architecture & Roadmap Proposals](#22-future-architecture--roadmap-proposals)
23. [Senior / Staff Interview Technical Discussion Map](#23-senior--staff-interview-technical-discussion-map)
24. [Resume-Ready Technical Building Blocks](#24-resume-ready-technical-building-blocks)
25. [Source-of-Truth Governance Rules](#25-source-of-truth-governance-rules)

---

# 1. Project Overview

### 1.1 What the Project Does
CodeSensei is a decoupled, asynchronous GitHub repository intelligence and exploration platform. Given any publicly accessible Git repository URL, CodeSensei performs automated shallow cloning, multi-language static code analysis (parsing abstract syntax trees and grammar definitions), constructs an interactive directed dependency graph, identifies circular architectural dependencies, calculates modular complexity and blast-radius metrics, and indexes the code for an interactive retrieval-augmented generation (RAG) conversational AI assistant that provides verifiable file-path and line-number citations.

### 1.2 The Problem It Solves
Software engineers spend up to 70% of onboarding or architectural auditing time reading unfamiliar source code. Traditional tools provide fragmented views:
- **IDEs & GitHub:** Display flat file trees and linear text files without global architectural context.
- **Linters:** Produce thousands of localized static warnings without revealing module coupling, structural layers, or circular import chains.
- **General-Purpose LLMs:** Hallucinate non-existent function names, obsolete package APIs, or file paths because they lack grounded, up-to-date repository context.

CodeSensei combines deterministic compiler graph analysis with retrieval-augmented conversational AI, allowing developers to explore architecture visually and verify AI answers against exact source code lines.

### 1.3 Intended Audience
- **Software Engineers & Technical Leads:** Conducting architectural audits, refactoring planning, and onboarding onto legacy codebases.
- **Open-Source Contributors:** Seeking a rapid understanding of project structure, high-complexity hotspots, and module dependency chains before submitting pull requests.

### 1.4 Core Capabilities
1. **Sandboxed Repository Ingestion:** Shallow clones Git repositories using the native `git` CLI with automated branch detection, strict array argument passing (`shell=False`), scrubbed environment (`GIT_TERMINAL_PROMPT=0`), configurable size caps (default 500MB via `API_MAX_REPO_SIZE_MB`), and timeouts (default 300s via `CLONE_TIMEOUT_SECONDS`).
2. **Multi-Tier Static Parsing:** Analyzes 10 programming languages (Python, JavaScript, TypeScript, Go, Rust, Java, C, C++, C#, and Ruby) using a 3-tier resilient registry: native Python `ast` for Python, Tree-sitter for robust LOC and cyclomatic branching decisions, and tuned Regex patterns for declarations.
3. **Graph Theory Dependency Modeling:** Resolves file-level import relationships into a directed graph, executing an iterative, recursion-free implementation of Tarjan's Strongly Connected Components (SCC) algorithm in $O(V+E)$ time to detect circular dependency cycles without blowing Python's recursion limit.
4. **On-Demand Blast-Radius Impact Analysis:** Traverses reverse-dependency graphs using Breadth-First Search (BFS) with exponential decay distance weighting ($\exp(-0.5 \cdot (d-1))$) and sigmoid saturation ($1.0 - \exp(-\sum \text{risk} / 8)$) via `ImpactService` to predict which upstream files break when a target file is modified.
5. **Architectural Layer Classification & Violation Detection:** Classifies files into 8 architectural layers (`ui`, `controllers`, `services`, `repositories`, `models`, `infrastructure`, `tests`, `other`), detects upward dependency layering violations, and generates interactive Mermaid flowcharts.
6. **Complexity & Calibrated Dead Code Heuristics:** Computes McCabe Cyclomatic Complexity, cognitive nesting proxies, and identifies unreferenced dead code candidates with calibrated confidence scores (0.5 for unimported non-entrypoint files; 0.7 for exported symbols unreferenced outside their definition).
7. **Streaming Context-Grounded AI Assistant:** Embeds symbol-aware code chunks into ChromaDB and streams conversational responses with verifiable file and line citations over Server-Sent Events (SSE) using Groq Cloud (Llama-3.3-70B) or local Ollama.
8. **Automated Markdown Documentation Generation:** Synthesizes structured markdown documentation (README, Architecture Guide, Developer Onboarding, and API Catalog) on demand, grounded in persisted database facts and metrics.

### 1.5 Main Use-Case Flow
```
User Submits GitHub URL ──► Async Enqueue (HTTP 202) ──► Background Worker Clones & Parses
                                                                    │
User Explores Visual Graph, Cycles & Chat ◄── SSE Streams Succeeded ◄┘
```

### 1.6 Key Design Characteristics
- **Strict Decoupling:** Static analysis is CPU- and disk-intensive; the API accepts jobs in milliseconds and delegates work to background workers via Redis Queue (RQ).
- **Zero-Cost Free-Tier Engineering:** Runs entirely on free-tier serverless services (Neon PostgreSQL, Upstash Redis, Groq Cloud, HuggingFace Inference API) with zero persistent compute charges.
- **Self-Healing Recovery:** Background reaper loops automatically detect and unwedge crashed worker jobs.
- **Dual-Transaction Streaming:** Disconnects database connections during long LLM streams to prevent connection pool exhaustion.

---

# 2. Current Feature Inventory

### 2.1 Repository Ingestion & Shallow Cloning
- **What It Does:** Accepts a GitHub repository URL, validates it against SSRF attacks, creates database tracking records, and queues background cloning.
- **How It Works:** `GitCloner` executes `git clone --depth 1 --single-branch` using the native `git` CLI via `subprocess.run(shell=False)` in a temporary workspace (`/var/lib/codesensei/workspaces/<slug>`). Strips all `GIT_*` environment variables and injects `GIT_TERMINAL_PROMPT=0` so private repositories fail fast without blocking on interactive credential prompts.
- **Frontend Components:** `RepoSubmissionModal.tsx`, `DashboardHeader.tsx`.
- **Backend Modules:** `backend/app/api/v1/endpoints/repositories.py`, `backend/app/services/repository_service.py`, `analysis-engine/engine/cloning/git_cloner.py`.
- **APIs Involved:** `POST /api/v1/repositories`, `GET /api/v1/repositories/{id}/events`.
- **Database Entities:** `Repository`, `AnalysisJob`.
- **External Services:** GitHub HTTPS Git server.
- **Edge Cases:** Repository >500MB triggers `RepositoryTooLargeError`; slow networks trigger 300s `TimeoutExpired`; private repos fail with `GIT_TERMINAL_PROMPT=0`.
- **Current Limitations:** Public repositories only. Private repositories requiring user GitHub OAuth tokens are not implemented.

### 2.2 Multi-Language Static Code Analysis
- **What It Does:** Discovers source code files, filters build artifacts (`node_modules`, `.git`), and extracts symbols, imports, lines of code, and branching metrics across 10 programming languages.
- **How It Works:** `FileWalker` discovers files respecting `.gitignore` patterns. `AnalysisOrchestrator` runs a `ThreadPoolExecutor` (4 workers) dispatching files to `ParserRegistry`. Python files use native `ast.AST`; non-Python files use Tree-sitter for LOC/branches and `RegexParser` for symbols and imports.
- **Frontend Components:** `MetricsCard.tsx`, `LanguageBreakdownBar.tsx`.
- **Backend Modules:** `analysis-engine/engine/orchestrator.py`, `analysis-engine/engine/parsers/*`.
- **Database Entities:** `SourceFile`, `Symbol`, `Metric`.
- **Edge Cases:** Malformed binary files fall back from UTF-8 to `chardet` Latin-1; unparseable syntax falls back to regex.
- **Current Limitations:** Tree-sitter extracts LOC and cyclomatic branching, but relies on regex for non-Python symbol declarations. Cross-file type resolution (LSP) is not supported.

### 2.3 Interactive Dependency Graph & Circular Cycle Detection
- **What It Does:** Renders an interactive force-directed graph of file import dependencies, highlights circular dependency cycles, and filters by directory or language.
- **How It Works:** `GraphBuilder` maps import statements to file paths. Iterative `detect_cycles` function executes a stack-based Tarjan's Strongly Connected Components (SCC) algorithm in $O(V+E)$ time (preventing `RecursionError` on large graphs). Frontend renders via Cytoscape.js canvas with `cose` layout.
- **Frontend Components:** `DependencyGraph.tsx`, `GraphControls.tsx`, `CycleAlertBanner.tsx`.
- **Backend Modules:** `analysis-engine/engine/graph/builder.py`, `analysis-engine/engine/graph/cycles.py`, `backend/app/services/dependency_service.py`.
- **APIs Involved:** `GET /api/v1/repositories/{id}/dependencies`.
- **Database Entities:** `Dependency`, `SourceFile`.
- **Caching:** Full graph cached in Redis (`repo:<id>:graph`, TTL 3600s).
- **Current Limitations:** Edges represent file-level imports, not function-level call graphs.

### 2.4 Impact Analysis (Refactoring Blast Radius)
- **What It Does:** Calculates which files would be affected if a selected file is modified, returning ranked upstream dependents and an overall risk score.
- **How It Works:** On-demand backend service `ImpactService` traverses reverse dependency edges via Breadth-First Search (BFS) up to `max_depth` (default 5, bounded 1–20), calculating blast radius scores with exponential distance decay:
  $$\text{Score}(u) = \exp(-0.5 \cdot (\text{dist}(u, \text{source}) - 1))$$
  Overall repository risk is squashed via sigmoid saturation:
  $$\text{Risk}_{\text{total}} = 1.0 - \exp\left(-\frac{\sum \text{Score}}{8}\right)$$
- **Frontend Components:** `ImpactAnalysisPage.tsx`, `ImpactAnalysisPanel.tsx`, `FileImpactModal.tsx`.
- **Backend Modules:** `backend/app/services/impact_service.py`, `backend/app/api/v1/endpoints/impact.py`.
- **APIs Involved:** `POST /api/v1/repositories/{id}/impact`.
- **Current Limitations:** Does not perform semantic AST diffing; assumes any modification to a file impacts all upstream dependents equally.

### 2.5 Complexity & Dead Code Analysis
- **What It Does:** Identifies codebase hotspots: high cyclomatic/cognitive complexity files and potential unreferenced dead code symbols.
- **How It Works:** Measures decision branching (`if`, `while`, `for`, `case`, `catch`). Evaluates dead code via authoritative `analysis-engine/engine/dead_code/detector.py` heuristics: flags unimported files (confidence 0.5, excluding entrypoints like `main`, `cli`, `server`) and exported symbols unreferenced outside their definition (confidence 0.7).
- **Frontend Components:** `ComplexityPage.tsx`, `DeadCodePage.tsx`, `ComplexityTable.tsx`, `DeadCodePanel.tsx`.
- **Backend Modules:** `analysis-engine/engine/metrics/complexity.py`, `analysis-engine/engine/dead_code/detector.py`, `backend/app/services/metric_service.py`, `backend/app/services/dead_code_service.py`.
- **APIs Involved:** `GET /api/v1/repositories/{id}/complexity`, `GET /api/v1/repositories/{id}/dead-code`.
- **Database Entities:** `Metric`, `Symbol`.

### 2.6 Retrieval-Augmented Conversational AI Assistant
- **What It Does:** Answers architectural and implementation questions about the codebase with verifiable file-path and line-number citations.
- **How It Works:** Code chunks sliced along AST symbol boundaries are vectorized in ChromaDB. When asked a question, Chroma retrieves top-k chunks ($k=8$), which are assembled into a prompt and streamed over SSE from Groq (Llama-3.3-70B) or local Ollama. Supports both persistent session-based chat (`/chat-sessions/{id}/chat`) and stateless one-off chat (`/ai/chat`).
- **Frontend Components:** `AIAssistantPage.tsx`, `ChatPanel.tsx`, `MessageBubble.tsx`, `CitationChip.tsx`, `ContextTagBar.tsx`.
- **Backend Modules:** `backend/app/services/ai_service.py`, `backend/app/services/chat_session_service.py`, `analysis-engine/engine/ai/*`.
- **APIs Involved:** `POST /api/v1/chat-sessions/{id}/chat`, `POST /api/v1/ai/chat`, `GET /api/v1/chat-sessions/{id}`, `GET /api/v1/chat-sessions/{id}/messages`, `POST /api/v1/repositories/{id}/chat-sessions`, `GET /api/v1/repositories/{id}/chat-sessions`.
- **Database Entities:** `ChatSession`, `ChatMessage`.
- **External Services:** Groq Cloud API, HuggingFace Inference API, Ollama (optional local).
- **Current Limitations:** Ephemeral ChromaDB storage in free tier; rate limits on Groq free tier (30 requests/min).

### 2.7 Discover Hub & Social Starring
- **What It Does:** Community showcase of analyzed public repositories with language filtering, search, and GitHub-style starring.
- **How It Works:** Queries public repositories grouped by repository identity (`url` + `branch`), sorted by `star_count DESC`. Idempotent starring updates the `stars` join table and atomically increments/decrements the denormalized counter on `repositories`.
- **Frontend Components:** `DiscoverPage.tsx`, `StarredPage.tsx`, `RepoCard.tsx`, `StarButton.tsx`.
- **Backend Modules:** `backend/app/api/v1/endpoints/discover.py`, `backend/app/api/v1/endpoints/stars.py`, `backend/app/services/star_service.py`.
- **APIs Involved:** `GET /api/v1/discover/repositories`, `GET /api/v1/discover/repository`, `PUT /api/v1/repositories/{id}/star`, `DELETE /api/v1/repositories/{id}/star`, `GET /api/v1/me/stars`.
- **Database Entities:** `Repository`, `Star`, `User`.

### 2.8 Architectural Layer Exploration & Violation Detection
- **What It Does:** Discovers architectural layers, checks for lower-to-higher layer call violations, and renders a live Mermaid flowchart.
- **How It Works:** `classify_architecture` inspects file paths and import edges, grouping files into 8 defined tiers (`ui`, `controllers`, `services`, `repositories`, `models`, `infrastructure`, `tests`, `other`). Detects when an inner/lower layer illegally imports from an outer/higher layer (e.g. `models` importing `controllers`). Cached in Redis (`repo:<id>:architecture`).
- **Frontend Components:** `ArchitecturePage.tsx`, `MermaidViewer.tsx`.
- **Backend Modules:** `analysis-engine/engine/architecture/classifier.py`, `backend/app/services/architecture_service.py`, `backend/app/api/v1/endpoints/architecture.py`.
- **APIs Involved:** `GET /api/v1/repositories/{id}/architecture`.
- **Database Entities:** `Repository`, `SourceFile`, `Dependency`.

### 2.9 Automated Markdown Documentation Generation
- **What It Does:** Generates comprehensive, fact-grounded markdown documentation for analyzed codebases on demand.
- **How It Works:** `DocumentationService` queries persisted repository records, dependency graphs, file lists, and complexity metrics, feeding them into `DocumentationWriter` to synthesize tailored markdown for 4 document types: `README`, `ARCHITECTURE`, `ONBOARDING`, and `API`.
- **Backend Modules:** `backend/app/services/documentation_service.py`, `backend/app/api/v1/endpoints/documentation.py`, `analysis-engine/engine/ai/documentation_writer.py`.
- **APIs Involved:** `POST /api/v1/repositories/{id}/documentation`.
- **Database Entities:** `Repository`, `SourceFile`, `Dependency`, `Metric`.

### 2.10 User Profiles & Visibility Management
- **What It Does:** Provides public developer profile showcases and allows repository owners to toggle public/private access.
- **How It Works:** `ProfileService` renders public developer portfolios with analyzed repos and star metrics. `set_visibility` endpoint allows owners to toggle `is_public` boolean, controlling whether anonymous visitors can access the repository analysis or receive an IDOR-masked 404.
- **Frontend Components:** `ProfilePage.tsx`, `RepositoryListPage.tsx`.
- **Backend Modules:** `backend/app/api/v1/endpoints/users.py`, `backend/app/api/v1/endpoints/repositories.py`, `backend/app/services/profile_service.py`.
- **APIs Involved:** `GET /api/v1/users/{username}`, `GET /api/v1/users/{username}/repositories`, `PATCH /api/v1/repositories/{id}/visibility`, `DELETE /api/v1/repositories/{id}`.
- **Database Entities:** `User`, `Repository`.

---

# 3. System Architecture & Current-State Topology

### 3.1 Component Decomposition
1. **Frontend Client (React 18 SPA):** Vite-bundled SPA served by Nginx 1.27-alpine on port `:8080`. Manages UI state via Zustand and TanStack Query, rendering force-directed graphs via Cytoscape.js HTML5 canvas.
2. **Backend API Gateway (FastAPI 0.115):** Uvicorn-hosted async application on port `:8000`. Handles authentication, REST contracts, SSE event streaming, database transactions via SQLAlchemy 2.0 Async (`asyncpg`), and runs the background `AnalysisReaper` loop.
3. **Background Worker (Python RQ 2.0):** Standalone container running `SimpleWorker` in burst mode. Connects to Redis Queue, invokes the analysis engine, performs batch SQL persistence, and upserts vectors.
4. **Analysis Engine:** Pure, stateless Python library imported exclusively by the worker. Manages Git cloning, AST parsing, graph algorithms, and RAG chunking.
5. **Relational Database (PostgreSQL 16):** Hosted on Neon Serverless (production) or local container. System of record for 10 relational entities, enforcing partial unique constraints and cascading deletes.
6. **In-Memory Broker & Cache (Redis 7):** Hosted on Upstash (production) or local container. Serves as RQ job queue and API response cache.
7. **Vector Database (ChromaDB 0.5.5):** Standalone HTTP service storing code chunk embeddings partitioned by collection (`repo_<repository_id>`).

### 3.2 Current System Architecture Diagram

```mermaid
flowchart TB
    subgraph ClientLayer ["Client Layer"]
        Browser["Web Browser (React 18 SPA)"]
    end

    subgraph EdgeLayer ["Edge and Ingress Layer"]
        Nginx["Nginx Reverse Proxy on port 8080"]
    end

    subgraph ApplicationLayer ["Application Services"]
        Backend["FastAPI Backend on port 8000"]
        Worker["RQ Analysis Worker"]
        Engine["Analysis Engine Library"]
    end

    subgraph StatefulLayer ["Stateful Persistence Layer"]
        PG[("PostgreSQL 16 Database")]
        Redis[("Redis 7 Queue and Cache")]
        Chroma[("ChromaDB Vector Store")]
    end

    subgraph ExternalProviders ["External Managed Services"]
        GitHub["GitHub API and Git HTTPS"]
        Groq["Groq Cloud LLM API"]
        Ollama["Ollama Local Fallback"]
        HF["HuggingFace Inference API"]
    end

    Browser -->|HTTPS 8080| Nginx
    Nginx -->|Static Assets| Browser
    Nginx -->|Proxy Pass /api/v1| Backend

    Backend -->|OAuth Roundtrip| GitHub
    Backend -->|SQL Queries| PG
    Backend -->|Cache and Enqueue| Redis
    Backend -->|Vector Search| Chroma
    Backend -->|Streaming Chat| Groq
    Backend -.->|Local Chat Fallback| Ollama

    Redis -->|Dequeue Jobs| Worker
    Worker -->|Shallow Git Clone| GitHub
    Worker -->|Invoke Parsing| Engine
    Worker -->|Heartbeat and Persist| PG
    Worker -->|Upsert Vectors| Chroma
    Worker -->|Embeddings Inference| HF
    Worker -.->|Local Embeddings Fallback| Ollama

    classDef client fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1;
    classDef ingress fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px,color:#312e81;
    classDef app fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f;
    classDef engine fill:#f3e8ff,stroke:#7e22ce,stroke-width:2px,color:#581c87;
    classDef storage fill:#dcfce7,stroke:#15803d,stroke-width:2px,color:#14532d;
    classDef external fill:#fce7f3,stroke:#be185d,stroke-width:2px,color:#831843;

    class Browser client;
    class Nginx ingress;
    class Backend,Worker app;
    class Engine engine;
    class PG,Redis,Chroma storage;
    class GitHub,Groq,HF,Ollama external;
```

---

# 4. End-to-End User Flows & Sequence Traces

### 4.1 GitHub OAuth Authentication Flow
1. User clicks "Sign in with GitHub" on `/login`.
2. Frontend redirects browser to `GET /api/v1/auth/github/login`.
3. Backend generates a cryptographically random `state` token, signs it, sets an `httpOnly` cookie (`codesensei_oauth_state`, 600s TTL), and redirects to `https://github.com/login/oauth/authorize`.
4. User authorizes CodeSensei on GitHub; GitHub redirects back to `GET /api/v1/auth/github/callback?code=...&state=...`.
5. Backend verifies returned `state` against cookie. If valid, exchanges authorization `code` for GitHub access token via HTTPS POST.
6. Backend fetches user profile (`GET https://api.github.com/user`), upserts row in `users` table, and mints an HS256 JWT session token.
7. Backend sets JWT in an `httpOnly`, `SameSite=Lax`, `secure` cookie (`codesensei_session`, 7-day TTL) and redirects browser to `/dashboard`.

### 4.2 Repository Submission & Analysis Flow (Sequence Trace)

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as React SPA
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant Redis as Redis Queue and Cache
    participant Worker as RQ Worker
    participant Engine as Analysis Engine
    participant GitHub as GitHub Git HTTPS
    participant Chroma as ChromaDB

    User->>FE: Submit repository URL
    FE->>API: POST /api/v1/repositories
    API->>API: validate_github_url SSRF guard
    
    rect rgb(240, 248, 255)
        Note over API,DB: Transaction A: Create Repo and Job
        API->>DB: INSERT INTO repositories (status=pending)
        API->>DB: INSERT INTO analysis_jobs (status=queued)
        DB-->>API: job_id, repo_id
    end

    API->>Redis: enqueue analysis job
    Redis-->>API: rq_job_id
    API-->>FE: 202 Accepted with job_id
    FE->>API: GET /api/v1/repositories/{id}/events (SSE)

    Worker->>Redis: SimpleWorker burst mode dequeues job
    Worker->>DB: UPDATE analysis_jobs SET status=running, heartbeat_at=now
    Worker->>DB: UPDATE repositories SET status=analyzing
    API-->>FE: SSE event: running (progress 0)

    Note over Worker,GitHub: Step 1: Sandboxed Shallow Clone
    Worker->>GitHub: git clone --depth 1 --branch
    GitHub-->>Worker: Cloned Git workspace directory
    API-->>FE: SSE event: progress (stage clone, 10 percent)

    Note over Worker,Engine: Step 2: Walk and Concurrent Parse
    Worker->>Engine: AnalysisOrchestrator.run_on_path
    Engine->>Engine: FileWalker filters ignore patterns
    
    par ThreadPoolExecutor with 4 workers
        Engine->>Engine: Parse file 1 (Python AST / Tree-sitter / Regex)
        Engine->>Engine: Parse file 2 (Python AST / Tree-sitter / Regex)
        Engine->>Engine: Parse file N (Python AST / Tree-sitter / Regex)
    end

    loop Every 25 files processed
        Worker->>DB: UPDATE analysis_jobs SET progress=X, heartbeat_at=now
        API-->>FE: SSE event: progress (stage parse)
    end

    Note over Engine: Step 3: Graph, Cycles and Classification
    Engine->>Engine: GraphBuilder resolves dependency edges
    Engine->>Engine: Tarjan SCC detects circular dependency cycles
    Engine->>Engine: Compute cyclomatic and dead-code metrics
    Engine->>Engine: Classify architecture into module tiers
    Engine-->>Worker: RepositoryAnalysis result object

    rect rgb(245, 255, 245)
        Note over Worker,DB: Transaction B: Atomic Replace and Version Stamp
        Worker->>DB: DELETE FROM source_files WHERE repository_id = id
        Worker->>DB: Batch INSERT source_files
        Worker->>DB: Batch INSERT symbols, metrics, dependencies
        Worker->>DB: UPDATE repositories SET status=ready
        Worker->>DB: Commit Transaction B
    end

    Note over Worker,Chroma: Step 4: Best-Effort Vector Indexing
    Worker->>Worker: CodeChunker creates symbol-aware slices
    Worker->>Worker: Batch call embedding provider
    Worker->>Chroma: Upsert vectors and metadata
    Note over Worker,Chroma: Indexing failure caught and degraded gracefully

    Worker->>DB: UPDATE analysis_jobs SET status=succeeded, progress=100
    Worker->>Redis: Invalidate cached graphs
    API-->>FE: SSE event: succeeded (progress 100)
    FE->>FE: Invalidate TanStack Query caches and render dashboard
```

### 4.3 Streaming AI Chat Flow (Dual-Transaction Pattern)
1. User types question on `/repos/:id/chat` (optionally tagging file chips).
2. Frontend issues `POST /api/v1/chat-sessions/{id}/chat`.
3. **Transaction 1 (5ms):** API validates session ownership, verifies rate limits, reads last 20 messages, inserts `ChatMessage(role='user')`, updates `last_activity_at`, commits, and **closes the database connection**.
4. **Retrieval:** API queries ChromaDB collection `repo_<id>` for top-$k$ ($k=8$) cosine-similar code chunks, plus exact file fetches for any tagged chips.
5. **Streaming:** API formats system prompt with fenced code chunks, calls Groq API with `stream=True`, and yields SSE tokens (`event: token`) to the browser.
6. **Transaction 2 (5ms):** Upon stream completion, API opens a second short database transaction, inserts `ChatMessage(role='assistant', citations=...)`, commits, and closes connection.

---

# 5. Core Execution & Asynchronous Processing Engine

### 5.1 Pipeline Stage Breakdown
1. **SSRF Pre-Validation:** `validate_github_url` in `backend/app/core/security.py` ensures HTTPS scheme, `github.com` domain, port 443/none, and alphanumeric owner/repo regex before the background worker ever sees the job.
2. **Sandboxed Native Git Cloning:** `GitCloner` (`analysis-engine/engine/cloning/git_cloner.py`) invokes the native `git` CLI directly via `subprocess.run(shell=False)`. It injects `_scrubbed_env()` (stripping all host `GIT_*` environment variables and forcing `GIT_TERMINAL_PROMPT=0`) to ensure private repositories fail instantly without hanging on interactive credentials, and enforces a configurable directory size cap (default 500MB via `API_MAX_REPO_SIZE_MB`) and timeout (default 300s via `CLONE_TIMEOUT_SECONDS`).
3. **Ignore-Aware File Discovery:** `FileWalker` recursively discovers source files while pruning `.git`, `node_modules`, `vendor`, `__pycache__`, build targets, binaries, and patterns defined in `.gitignore`.
4. **Concurrent Multi-Tier Parsing:** Spawns a `ThreadPoolExecutor` with 4 worker threads. Python files parse into native Python `ast.AST`. Non-Python files invoke Tree-sitter for concrete syntax tree navigation (calculating accurate LOC and cyclomatic branching decisions without comment/string interference), delegating symbol declarations and imports to tuned regex patterns.
5. **Graph Resolution & Cycle Detection:** Resolves relative and module imports into canonical repository paths. Builds a directed graph and executes an iterative, recursion-free implementation of Tarjan's Strongly Connected Components (SCC) algorithm to identify circular dependency cycles.
6. **Architecture Classification & Dead-Code Heuristics:** Classifies files into 8 architectural tiers (`ui`, `controllers`, `services`, `repositories`, `models`, `infrastructure`, `tests`, `other`), detects upward layering violations, and computes dead code candidate confidences (`0.5` for unimported files, `0.7` for unreferenced symbols). *(Note: Blast-radius impact analysis is computed on-demand via `ImpactService` when requested by the client, not during worker ingestion).*
7. **Atomic PostgreSQL Ingestion:** Wraps persistence in an explicit transaction scope. Hard-deletes previous `source_files` for the repository (cascading cleanly across symbols, metrics, and dependencies) and executes bulk inserts via SQLAlchemy Core `insert()`. Updates repository `status = ready`.
8. **Symbol-Aware RAG Chunking & Vector Upsert:** Slices code files along class/function boundaries (target 60 lines, max 200 lines, 6 lines overlap). Generates 384-dimensional embeddings via HuggingFace Inference API or Ollama. Upserts vectors to ChromaDB collection `repo_<repository_id>`.

### 5.2 Failure & Self-Healing Architecture
- **Worker Heartbeat Tracking:** The background worker updates `heartbeat_at = now()` on `analysis_jobs` at every stage transition and periodically every 25 files processed during parsing.
- **Analysis Reaper (`backend/app/services/analysis_reaper.py`):** The FastAPI application runs an asynchronous lifespan background loop (`run_reaper_loop`) every 60 seconds by default (configurable via `ANALYSIS_REAPER_INTERVAL_SECONDS`, clamped to minimum 10s). It executes an atomic `UPDATE` querying for `running` jobs with `now() - heartbeat_at > 900s` (`ANALYSIS_RUNNING_HEARTBEAT_TIMEOUT_SECONDS`) and `queued` jobs with `now() - queued_at > 1800s` (`ANALYSIS_QUEUED_TIMEOUT_SECONDS`). It marks those jobs `failed`, marks their parent repositories `failed`, and immediately clears the partial unique index (`uq_active_job_per_repository`), unblocking user retries.
- **Graceful Vector Degradation:** If ChromaDB or the HuggingFace API is unavailable during indexing, the worker catches `IndexingDegraded`, logs a warning, sets `indexed_chunks = 0`, and still completes the analysis as `ready`. Code browsing, graph visualization, and complexity tables remain 100% operational.

---

# 6. Data Model & Relational Database Schema

### 6.1 Database Entity-Relationship Diagram (ERD)

```mermaid
erDiagram
    USERS ||--o{ REPOSITORIES : owns
    USERS ||--o{ CHAT_SESSIONS : participates_in
    USERS ||--o{ STARS : stars

    REPOSITORIES ||--o{ ANALYSIS_JOBS : triggers
    REPOSITORIES ||--o{ SOURCE_FILES : contains
    REPOSITORIES ||--o{ CHAT_SESSIONS : scoped_to
    REPOSITORIES ||--o{ STARS : starred_by

    SOURCE_FILES ||--o{ SYMBOLS : declares
    SOURCE_FILES ||--o| METRICS : has_metrics
    SOURCE_FILES ||--o{ DEPENDENCIES : outgoing_deps
    SOURCE_FILES ||--o{ DEPENDENCIES : incoming_deps

    CHAT_SESSIONS ||--o{ CHAT_MESSAGES : contains

    USERS {
        uuid id PK
        bigint github_id "Unique GitHub account ID"
        varchar username "Indexed username handle"
        varchar display_name "Nullable display name"
        varchar email "Nullable user email"
        varchar avatar_url "Nullable avatar link"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    REPOSITORIES {
        uuid id PK
        uuid owner_id FK "References users.id"
        boolean is_public "Controls anonymous access"
        varchar url "GitHub repository URL"
        varchar branch "Nullable git branch"
        varchar default_branch "Nullable default branch"
        varchar name "Repo directory name"
        varchar owner "GitHub organization or user"
        varchar status "pending, cloning, analyzing, ready, failed"
        varchar error_message "Nullable failure detail"
        timestamptz analyzed_at "Timestamp of last analysis"
        varchar commit_hash "Analyzed commit SHA"
        integer analysis_version "Logic version"
        integer pipeline_version "Orchestration version"
        integer schema_version "Persisted shape version"
        varchar embedding_model "Model signature"
        integer file_count "Denormalized file count"
        integer total_lines "Denormalized line count"
        varchar languages "Top languages breakdown"
        integer star_count "Denormalized star count"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    ANALYSIS_JOBS {
        uuid id PK
        uuid repository_id FK "References repositories.id"
        varchar status "queued, running, succeeded, failed, cancelled"
        varchar rq_job_id "Redis Queue job ID"
        varchar error "Nullable error detail"
        timestamptz queued_at "Enqueue timestamp"
        timestamptz started_at "Worker start timestamp"
        timestamptz completed_at "Terminal timestamp"
        timestamptz heartbeat_at "Worker liveness heartbeat"
        integer progress "Percentage 0 to 100"
        varchar progress_message "Progress status text"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    SOURCE_FILES {
        uuid id PK
        uuid repository_id FK "References repositories.id"
        varchar path "Relative file path"
        varchar language "Detected language"
        integer line_count "Total lines"
        bigint size_bytes "File size in bytes"
        varchar sha256 "SHA-256 hash"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    SYMBOLS {
        uuid id PK
        uuid file_id FK "References source_files.id"
        varchar name "Identifier name"
        varchar qualified_name "Scoped identifier"
        varchar kind "function, method, class, interface, struct, enum, variable, constant, type_alias, module"
        integer line_start "Starting line"
        integer line_end "Ending line"
        boolean is_exported "Exported boolean"
        boolean is_used "Reachability flag"
        integer usage_count "References count"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    DEPENDENCIES {
        uuid id PK
        uuid from_file_id FK "References source_files.id"
        uuid to_file_id FK "References source_files.id"
        varchar kind "import, inheritance, call, instantiation, reference"
        varchar symbol "Target symbol"
        integer line "Source line number"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    METRICS {
        uuid id PK
        uuid file_id FK "Unique reference to source_files.id"
        integer cyclomatic "Cyclomatic complexity"
        integer cognitive "Cognitive complexity"
        integer lines_of_code "Executable LOC"
        integer function_count "Total functions"
        integer class_count "Total classes"
        numeric dead_code_score "Unreachability score"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    CHAT_SESSIONS {
        uuid id PK
        uuid user_id FK "References users.id"
        uuid repository_id FK "References repositories.id"
        varchar title "Session title"
        timestamptz last_activity_at "Last message activity"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    CHAT_MESSAGES {
        uuid id PK
        uuid session_id FK "References chat_sessions.id"
        varchar role "user or assistant"
        text content "Message body"
        jsonb citations "Assistant citations"
        jsonb attached_context "User attached files"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }

    STARS {
        uuid id PK
        uuid user_id FK "References users.id"
        uuid repository_id FK "References repositories.id"
        timestamptz created_at "Created timestamp"
        timestamptz updated_at "Updated timestamp"
    }
```

### 6.2 Key Relational Constraints & Invariants
1. **Mutual Exclusion on Active Jobs:** Alembic migration `0006_active_job_unique.py` enforces:
   ```sql
   CREATE UNIQUE INDEX uq_active_job_per_repository ON analysis_jobs (repository_id) WHERE status IN ('queued', 'running');
   ```
   Guarantees zero duplicate active analysis jobs at the database engine level.
2. **Per-User Repository Scope:** `uq_repositories_owner_id_url_branch` enforces `(owner_id, url, branch)` uniqueness, allowing users to isolate their own analysis copies.
3. **Repository Path Uniqueness:** `uq_source_files_repo_path` enforces `(repository_id, path)` uniqueness in `source_files`.
4. **Deterministic Edge Uniqueness:** `uq_dependencies_edge` enforces `(from_file_id, to_file_id, kind, symbol)` uniqueness in `dependencies`.
5. **Strict 1-to-1 File Metrics:** `metrics.file_id` is marked `unique=True` ensuring exactly one metric record per source file.
6. **Idempotent Starring:** `uq_stars_user_repository` enforces `(user_id, repository_id)` uniqueness.
7. **Cascading Deletions:** Every child table references its parent with `ON DELETE CASCADE`. Deleting a repository atomically purges jobs, files, symbols, metrics, dependencies, stars, and chat sessions.

---

# 7. Comprehensive API Reference

The backend exposes **38 distinct API routes** (35 mounted under `/api/v1`, plus health, readiness, and metrics probes mounted both at root and under `/api/v1`):

| Method | Path | Auth | Purpose | Key Validation / Errors |
| :--- | :--- | :---: | :--- | :--- |
| `POST` | `/auth/dev-login` | None | Instant local mock login for development | 403 Forbidden if `APP_ENV=production` |
| `GET` | `/auth/github/login` | None | Initiates GitHub OAuth 2.0 authorization | Sets signed `codesensei_oauth_state` CSRF cookie |
| `GET` | `/auth/github/callback` | None | Exchanges OAuth code for JWT session cookie | 400 Bad Request if state mismatch or code invalid |
| `POST` | `/auth/logout` | Optional | Clears session authentication cookie | Sets `codesensei_session` cookie `max_age=0` |
| `GET` | `/auth/me` | User | Returns authenticated profile & identity | 401 Unauthorized if session cookie is missing |
| `POST` | `/repositories` | User | Submits GitHub repository for background analysis | 400 SSRF invalid URL; 409 if already queued/running |
| `GET` | `/repositories` | User | Paginated list of owned repositories | Supports `page`, `page_size`, `status` filtering |
| `GET` | `/repositories/{id}` | Optional | Detailed repository metadata & status | 404 Not Found if private & unowned (IDOR mask) |
| `PATCH`| `/repositories/{id}/visibility`| User | Toggles repository `is_public` boolean | 403 Forbidden if not repository owner |
| `DELETE`| `/repositories/{id}` | User | Atomically deletes repository and child data | 403 if not owner; cascades in DB and ChromaDB |
| `POST` | `/repositories/{id}/analyze` | User | Re-triggers full analysis for existing repository | 409 Conflict if active job already running |
| `GET` | `/repositories/{id}/jobs` | Optional | Lists historical analysis jobs for repository | 404 if unowned private repository |
| `GET` | `/repositories/{id}/jobs/latest` | Optional | Retrieves the most recent analysis job | 404 if unowned private repository |
| `GET` | `/repositories/{id}/events` | Optional | Real-time SSE stream of job progress | `text/event-stream`; periodic heartbeat keepalives |
| `GET` | `/repositories/{id}/dependencies`| Optional | Returns graph nodes, edges, and cycles | 404 if unowned; cached in Redis (`repo:<id>:graph`) |
| `POST` | `/repositories/{id}/impact` | Optional | On-demand reverse-dependency blast radius | Validates `file_path` exists; returns BFS risk scores |
| `GET` | `/repositories/{id}/complexity` | Optional | Top files ranked by cyclomatic/cognitive metric | `top_n` query parameter (1–100, default 10) |
| `GET` | `/repositories/{id}/dead-code` | Optional | Lists candidate unreferenced dead code symbols | Filtered by heuristic confidence (0.5 or 0.7) |
| `GET` | `/repositories/{id}/architecture`| Optional | 8-layer architecture report & Mermaid diagram | Cached in Redis (`repo:<id>:architecture`) |
| `POST` | `/repositories/{id}/documentation`| Optional| Synthesizes fact-grounded markdown documentation | Accepts `kind`: `README`, `ARCHITECTURE`, `ONBOARDING`, `API` |
| `POST` | `/repositories/{id}/chat-sessions`| User | Starts a new AI chat conversation for repository | 404 if repository is private and unowned |
| `GET` | `/repositories/{id}/chat-sessions`| User | Paginated list of user's chats for repository | Strictly scoped to authenticated user ID |
| `GET` | `/chat-sessions/{session_id}` | User | Retrieves chat session metadata and title | 404 if session belongs to another user (IDOR mask) |
| `PATCH`| `/chat-sessions/{session_id}` | User | Renames chat session title | 404 if session belongs to another user |
| `DELETE`| `/chat-sessions/{session_id}`| User | Deletes chat session and all messages | 204 No Content; 404 if session not owned |
| `GET` | `/chat-sessions/{session_id}/messages`| User | Paginated chat message history | Page size 1–200, default 100 |
| `POST` | `/chat-sessions/{session_id}/chat`| User | Sends question, streams tokens with citations | SSE stream; dual-transaction DB connection release |
| `POST` | `/ai/chat` | Optional | Stateless one-off streamed question & answer | SSE stream; does not persist conversation session |
| `PUT` | `/repositories/{id}/star` | User | Stars repository idempotently | Increments denormalized star counter |
| `DELETE`| `/repositories/{id}/star` | User | Removes star from repository idempotently | Decrements denormalized star counter |
| `GET` | `/me/stars` | User | Paginated list of user's starred repositories | Annotates `starred=true` for all items |
| `GET` | `/discover/repositories` | None | Public directory of repositories | Supports `language`, `q`, `sort`, pagination |
| `GET` | `/discover/repository` | None | Grouped overview of public analyses by URL & branch| Annotates viewer star state if signed in |
| `GET` | `/users/{username}` | None | Public developer profile card | 404 if user handle does not exist |
| `GET` | `/users/{username}/repositories`| None | Public developer's analyzed repositories | Paginated; sortable by stars or date |
| `GET` | `/healthz` | None | Basic liveness probe (root and `/api/v1`) | Returns 200 OK `{"status": "ok"}` |
| `GET` | `/readyz` | None | Deep readiness probe (root and `/api/v1`) | Verifies active connections to Postgres, Redis, Chroma |
| `GET` | `/metrics` | None | Prometheus scrape target (root and `/api/v1`) | Exposes request latency histograms and counters |

---

# 8. Authentication, Authorization & Session Management

### 8.1 Authentication Architecture
- **Stateless Cookie JWT:** Mints HS256-signed JWTs containing `sub` (user UUID), `gh` (GitHub numeric ID), and `exp` (7-day timestamp).
- **Cookie Security Flags:** Stored exclusively in cookie named `codesensei_session` configured with `httponly=True`, `samesite="lax"`, `secure=(APP_ENV == "production")`, and `max_age=604800`.
- **Zero Local Password Storage:** The platform maintains zero user passwords; authentication is completely delegated to GitHub OAuth 2.0.

### 8.2 Authorization & IDOR Masking
- **Dependency Guard (`verify_repository_access`):** Applied on all repository endpoints.
  - If user is repository owner $\rightarrow$ Access Granted.
  - If repository has `is_public = True` $\rightarrow$ Read-Only Access Granted.
  - If repository has `is_public = False` and user is NOT owner (or anonymous) $\rightarrow$ Returns **`404 Not Found`** (never `403 Forbidden`).
  - **Security Invariant:** Returning 404 prevents malicious actors from enumerating private repository existence via IDOR attacks.

---

# 9. Application Security & Hardening Realities

| Defense Vector | Implementation Reality | Location in Code | Limitation |
| :--- | :--- | :--- | :--- |
| **SSRF** | `validate_github_url` enforces https, domain `github.com`, port 443/none, no credentials, regex `/<owner>/<repo>`. | [security.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/security.py#L23) | Only validates hostname; does not inspect IP post-DNS. |
| **Path Traversal** | `safe_join` verifies target path resides within workspace root and rejects backslashes (`\`) unconditionally. | [security.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/security.py#L78) | None; robust path sandboxing. |
| **Command Injection** | Branch names validated via regex; `GitCloner` invokes native `git` executable passing arguments as discrete array via `subprocess.run(shell=False)`. | [security.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/security.py#L23), [git_cloner.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/cloning/git_cloner.py#L76) | None; shell execution completely disabled. |
| **SQL Injection** | Exclusively uses SQLAlchemy 2.0 ORM with parameterized query compilation. | Across all services | Raw unescaped SQL execution is forbidden. |
| **XSS** | JWT session stored exclusively in `httpOnly` cookies; inaccessible to JavaScript `document.cookie`. | [auth.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/api/v1/endpoints/auth.py#L65) | Requires strict Nginx CSP headers for full defense. |
| **OAuth CSRF** | Cryptographically random `state` cookie signed and verified upon callback (600s TTL). | [auth.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/api/v1/endpoints/auth.py#L32) | None; standard state verification. |
| **Rate Limiting** | `RateLimitMiddleware` enforces in-memory sliding window (60 requests/minute per client IP). | [middleware.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/core/middleware.py#L59) | In-memory only; limits reset on restart or pod scaling. |

---

# 10. Error Handling, Failure Scenarios & Reliability

### 10.1 Global Exception Handlers
Application errors are intercepted by centralized FastAPI exception handlers registered in `backend/app/main.py` via `_install_exception_handlers(app)`:
- **`DomainError`:** Mapped to domain `status_code` (e.g. 400, 404, 409, 503) returning:
  ```json
  {
    "error": "analysis_already_running",
    "message": "An analysis is already in progress for this repository.",
    "details": {}
  }
  ```
- **`RequestValidationError`:** Mapped to HTTP 422 with validation errors list in `details`.
- **`Exception` (Unhandled):** Intercepted, logged with full server-side stack trace, and returned as generic HTTP 500 (`{"error": "internal_error", "message": "An unexpected error occurred"}`) to prevent internal environment leakage.

### 10.2 Failure Scenarios & Self-Healing Matrix
- **Redis Queue Outage:** `JobDispatcher` catches `redis.exceptions.RedisError`, logs error, raises `QueueUnavailableError` $\rightarrow$ maps to **HTTP 503 Service Unavailable**. The database transaction creating the repository is rolled back cleanly.
- **Worker OOM-Kill / Mid-Flight Crash:** `run_reaper_loop` background task in `backend/app/services/analysis_reaper.py` detects missing heartbeat (>900s default) or unstarted queue jobs (>1800s default), marks job `failed`, marks repository `failed`, and releases the database partial unique index.
- **Client Disconnect During LLM Stream:** Handled via **Dual-Transaction Pattern**. User question was already committed in Tx 1. When the client disconnects, FastAPI terminates the generator; uncommitted assistant tokens are dropped without rolling back user history.
- **ChromaDB Outage:** Best-effort vector indexing swallows `IndexingDegraded`. Repository analysis still marks `ready`. Code graph, metrics, and dead code tools remain 100% operational.

---

# 11. Frontend Architecture & State Topology

### 11.1 Client-Side Division of Concerns
- **Routing & Complete Page Inventory (14 Pages):** Built with React Router v6 using declarative nested layouts (`AppLayout`, `RepoLayout`, `AuthLayout`):
  1. `LoginPage.tsx` — GitHub OAuth initiation and developer mock login.
  2. `RepositoryListPage.tsx` — User's personal dashboard of owned analyses with visibility badges.
  3. `RepositoryDashboardPage.tsx` — Main analysis dashboard displaying metrics summary, languages, and navigation cards.
  4. `DependencyGraphPage.tsx` — Interactive Cytoscape.js force-directed graph viewer with cycle detection overlays.
  5. `ImpactAnalysisPage.tsx` — Refactoring blast-radius calculator with file search, upstream tree, and risk gauge.
  6. `ArchitecturePage.tsx` — 8-layer architecture classification view with interactive Mermaid flowchart.
  7. `ComplexityPage.tsx` — Hotspot ranking table sorting files by cyclomatic and cognitive complexity.
  8. `DeadCodePage.tsx` — Candidate unused symbols table with calibrated confidence chips and file references.
  9. `AIAssistantPage.tsx` — Multi-session conversational code assistant with verifiable line citations.
  10. `DiscoverPage.tsx` — Community repository showcase with search and popularity star sorting.
  11. `RepositoryAnalysesPage.tsx` — Grouped history of analyses for a given repository URL across users.
  12. `StarredPage.tsx` — Authenticated user's bookmarked repository feed.
  13. `ProfilePage.tsx` — Public developer portfolio showcase.
  14. `NotFoundPage.tsx` — 404 error page.

- **State Management Topology (3 Zustand Stores):**
  - `nodeContextStore`: Global cross-surface bridge connecting visual graph node clicks and architecture components directly to the AI chat input via attached context chips.
  - `themeStore`: Dark / light mode persistence and toggle state.
  - `uiStore`: Sidebar collapse states, modal dialogs, and drawer toggles.

- **Server Cache & Synchronization:** TanStack Query v5 handles server data fetching, query deduplication, background re-fetching, and cache invalidation upon SSE job completion.
- **Graph Visualization:** Cytoscape.js canvas rendering with force-directed physics computed in background Web Workers, preventing main UI thread layout freezes.

---

# 12. Backend Architecture & Service Boundaries

### 12.1 Layered Architecture Pattern
```
routers (HTTP / SSE / Validation)
  └── services (Business Logic / Orchestration / Transactions)
        └── models & persistence (SQLAlchemy ORM / Raw Core Inserts)
```
- **Stateless API:** Zero persistent in-memory session state; any API instance can service any request.
- **Asynchronous Lifespan Management:** Uses FastAPI `lifespan(app)` context manager to start and cleanly cancel background tasks (`AnalysisReaper`).
- **Hermetic Library Boundaries:** The `analysis-engine` package is completely decoupled from FastAPI and SQLAlchemy, making it independently testable and portable.

---

# 13. Technology Stack & Architectural Alternatives

| Technology | Where Used | Why It Fits This Project | Reasonable Alternative | Why Alternative Was Not Chosen |
| :--- | :--- | :--- | :--- | :--- |
| **FastAPI 0.115** | Backend API | Native async I/O fits SSE streaming & concurrent queries; Pydantic v2 validation. | Django / Flask | Django is heavyweight with sync ORM baggage; Flask lacks native async/OpenAPI. |
| **PostgreSQL 16** | System of Record | ACID transactions for bulk batch persistence; partial unique indexing for concurrency. | MongoDB | MongoDB lacks atomic partial unique constraints and relational cascading deletes. |
| **Redis Queue (RQ)**| Background Queue | Lightweight FIFO queue over Redis; `SimpleWorker(burst=True)` handles serverless timeouts. | Celery | Celery has high configuration overhead and hangs on serverless Redis idle disconnects. |
| **ChromaDB 0.5.5** | Vector DB | Standalone HTTP vector store with native collection-level isolation (`repo_<id>`). | Qdrant / Pinecone | Standalone Chroma runs with minimal memory footprint in free tier. |
| **React 18 + Vite 5**| Frontend SPA | Fast HMR; optimal for heavy client-side canvas rendering (Cytoscape.js). | Next.js (SSR) | SSR offers zero performance benefit for client-side force-directed canvas graphs. |
| **Cytoscape.js 3.30**| Graph Viewer | Canvas-based rendering maintains 60 FPS across 1,000+ nodes; built-in physics layouts. | D3.js / React Flow| React Flow DOM nodes cause layout thrashing on >500 nodes; D3 requires manual layout code. |
| **Groq Cloud API** | LLM Inference | Free tier Llama-3.3-70B running at ~300 tokens/second for instant SSE streaming. | OpenAI GPT-4o | OpenAI has per-token costs; Groq provides free high-speed open-weights inference. |

---

# 14. Engineering Decisions & Trade-Off Matrix

### 1. Concurrency Mutual Exclusion via PostgreSQL Partial Unique Index
- **Decision:** Use `CREATE UNIQUE INDEX ... WHERE status IN ('queued', 'running')` instead of distributed Redis locks (Redlock).
- **Benefits:** Zero external network hops; immune to clock drift or Redis master-replica failovers; ACID consistency.
- **Trade-off:** Confines mutual exclusion enforcement strictly to PostgreSQL.
- **When It Stops Working:** When submissions exceed 10,000 req/sec across sharded databases.

### 2. Dual-Transaction Pattern for AI Streaming
- **Decision:** Commit user turn in Tx 1, close DB connection during LLM stream, commit assistant turn in Tx 2.
- **Benefits:** Prevents database connection pool exhaustion under small connection pools (`pool_size=5`); preserves user question on client disconnect.
- **Trade-off:** Two transactions per chat turn instead of one.
- **When It Stops Working:** Remains valid at any scale.

### 3. Tree-sitter for Metrics + Regex for Declarations
- **Decision:** Use Tree-sitter for LOC and cyclomatic branching; delegate symbol declarations to Regex on non-Python code.
- **Benefits:** Keeps Docker container <250MB; parses 10 languages without downloading gigabytes of compiler toolchains.
- **Trade-off:** Regex cannot resolve complex macro expansions or destructured TypeScript imports.
- **When It Stops Working:** When users demand deep cross-file compiler type resolution.

---

# 15. Scaling the System (Stages 1 through 3)

### Stage 1: Current Architecture (Single Host / Free Tier POC)
- **Characteristics:** 1 FastAPI process, 1 RQ worker, Neon PostgreSQL (max 5 connections), Upstash Redis, ChromaDB on single host.
- **Throughput:** ~100 active users, ~500 repositories, 1–2 concurrent analysis jobs.

---

### Stage 2: Growing Usage (100K Users, 50K Repositories) `[PROPOSED / SCALING OPTION]`
- **Bottlenecks:** API CPU saturation, Redis connection limits, worker disk contention.
- **Architectural Evolutions:**
  1. **Stateless API Cluster:** 3–5 FastAPI replicas behind AWS Application Load Balancer.
  2. **Managed Redis Cluster:** Migrate to Amazon ElastiCache. Implement Redis-backed token-bucket rate limiting via Lua scripts.
  3. **Read Replicas & PgBouncer:** Route read queries (Discover hub, graph views) to PostgreSQL read replicas; pool connections via PgBouncer.
  4. **Tiered Priority Queues:** Partition queue into `queue:small`, `queue:medium`, and `queue:large` based on repo file size.

---

### Stage 3: Enterprise Scale (1M+ Users, 500K Repositories) `[PROPOSED / SCALING OPTION]`

```mermaid
flowchart TB
    Client["Clients, Mobile, Web"] --> CDN["Cloudflare Edge and Global Cache"]
    CDN --> Ingress["Kubernetes NGINX Ingress Controller"]

    subgraph K8sCluster ["Amazon EKS Cluster"]
        subgraph APIDeployment ["FastAPI Deployment with HPA"]
            APIPods["FastAPI Pods (10-30 Replicas)"]
        end

        subgraph KEDAWorkers ["Worker Deployments with KEDA"]
            QSmallW["Small Repo Workers"]
            QMedW["Medium Repo Workers"]
            QLargeW["Large Repo Workers"]
        end

        LLMGateway["Internal LLM Gateway Router"]
    end

    subgraph PersistentTier ["Distributed Data Tier"]
        DBCluster[("PostgreSQL Aurora Multi-AZ")]
        RedisHA[("Redis HA Cluster")]
        QdrantCluster[("Qdrant Sharded Vector Cluster")]
        S3[("AWS S3 Object Storage")]
    end

    Ingress --> APIPods
    APIPods -->|Writes| DBCluster
    APIPods -->|Reads| DBCluster
    APIPods -->|Enqueue and Token Bucket| RedisHA
    APIPods -->|Vector Query| QdrantCluster
    APIPods -->|Streaming Chat| LLMGateway

    RedisHA -->|Priority Queues| KEDAWorkers
    KEDAWorkers -->|Persist Results| DBCluster
    KEDAWorkers -->|Upsert Vectors| QdrantCluster
    KEDAWorkers -->|Tarball Snapshots| S3

    classDef client fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1;
    classDef ingress fill:#e0e7ff,stroke:#4f46e5,stroke-width:2px,color:#312e81;
    classDef app fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#78350f;
    classDef engine fill:#f3e8ff,stroke:#7e22ce,stroke-width:2px,color:#581c87;
    classDef storage fill:#dcfce7,stroke:#15803d,stroke-width:2px,color:#14532d;

    class Client,CDN client;
    class Ingress ingress;
    class APIPods,QSmallW,QMedW,QLargeW app;
    class LLMGateway engine;
    class DBCluster,RedisHA,QdrantCluster,S3 storage;
```

---

# 16. Bottlenecks & Critical Breaking Points

1. **Worker Disk I/O & Clone Space:** Cloned repos written to local `/var/lib/codesensei/workspaces`. If 10 large repos clone concurrently, worker disk can fill up. *Mitigation:* Clean workspaces in `finally` block; mount high-IOPS NVMe scratch storage.
2. **Groq Cloud API Rate Limits:** Free tier capped at 30 requests/min and 14,400 req/day. *Mitigation:* Fail gracefully over SSE; implement automatic fallback to local Ollama.
3. **ChromaDB Memory Footprint:** Chroma loads vector collections into RAM. At >10,000 repos, memory exhausts. *Mitigation:* Migrate to distributed Qdrant with on-disk HNSW indexes.
4. **PostgreSQL Write Locks on Re-Analysis:** Cascading wipe-and-replace deletes 20,000+ rows, acquiring exclusive table locks. *Mitigation:* Replace hard deletes with soft deletes (`is_active=False`) and async background vacuuming.

---

# 17. Comprehensive Edge-Case Inventory

| Category | Specific Scenario | Status | Verified Codebase Handling |
| :--- | :--- | :---: | :--- |
| **Input** | Empty / invalid GitHub URL | **Handled** | `validate_github_url` regex rejects before database insert. |
| **Security**| SSRF (`http://169.254.169.254`) | **Handled** | Blocked: scheme must be https; host must be `github.com`. |
| **Security**| Path Traversal (`../../etc/passwd`)| **Handled** | `safe_join` verifies path resolves within workspace root. |
| **Security**| Branch Command Injection (`--upload-pack`)| **Handled** | `validate_branch_name` blocks leading dashes; args passed as list. |
| **Security**| IDOR Access to Private Repository | **Handled** | `verify_repository_access` raises HTTP 404 (never 403). |
| **Queue** | Duplicate Simultaneous Submission | **Handled** | `uq_active_job_per_repository` raises `IntegrityError` $\rightarrow$ 409. |
| **Queue** | Redis Outage During Submission | **Handled** | `JobDispatcher` catches error $\rightarrow$ 503; DB rolls back cleanly. |
| **Worker**| Worker OOM / Container Crash | **Handled** | `AnalysisReaper` loop fails jobs with heartbeat >900s (queued >1800s). |
| **Worker**| Cloned Repo >500MB | **Handled** | `GitCloner` calculates disk usage, raises `RepositoryTooLargeError`. |
| **Parser**| Malformed Binary File | **Handled** | UTF-8 decode $\rightarrow$ `chardet` Latin-1 guess $\rightarrow$ skips binary. |
| **AI** | ChromaDB Outage During Indexing | **Handled** | Best-effort indexing swallows error; analysis marks `READY`. |
| **AI** | Client Disconnect Mid-Stream | **Handled** | Dual-Transaction pattern preserves user question in DB. |
| **RateLimit**| Single IP Flooding Endpoints | **Partially** | In-memory sliding window limits IP; resets on restart. |
| **Scale** | Head-of-line Blocking in Queue | **Not Handled**| Single FIFO queue; large repos block small microservices. |

---

# 18. Testing Architecture & Verification Reality

### 18.1 Test Suites in Repository
- **Unit Tests (`analysis-engine/tests/`, `backend/tests/unit/`):** Hermetic pytest suite testing Python AST, Tree-sitter LOC, Tarjan's SCC, dead code reachability, symbol-aware chunking, and SSRF validators with zero external network or database dependencies.
- **Integration Tests (`backend/tests/integration/`, `worker/tests/`):** Full FastAPI endpoint tests running with real PostgreSQL 16 and Redis service containers in CI. Runs real Alembic migrations against `codesensei_test`.
- **Contract Tests (`tests/contract/`):** Validates OpenAPI specification conformance against Pydantic schemas.
- **End-to-End Tests (`frontend/tests/e2e/`):** Playwright automated browser test (`repository-flow.spec.ts`) executing Login $\rightarrow$ Submit $\rightarrow$ SSE $\rightarrow$ Graph render.
- **Load Tests (`tests/load/locustfile.py`):** Locust scenario simulating user traffic distributions.

---

# 19. Observability, Telemetry & Operations

- **Structured Logging:** Uses `structlog` emitting JSON to `stdout`. Every HTTP request binds a unique `request_id` (`X-Request-ID` header) tracked across database queries and error logs.
- **Prometheus Metrics:**
  - API exposes `/metrics` collecting HTTP request counts, response latency histograms (`http_request_duration_seconds`), and active SSE streams.
  - Worker exposes standalone Prometheus HTTP server on port `:9101` (`worker_jobs_processed_total`, `analysis_duration_seconds`).
- **Health Probes:**
  - `GET /healthz`: Basic liveness ping.
  - `GET /readyz`: Deep readiness probe asserting active connectivity to PostgreSQL, Redis, and ChromaDB.

---

# 20. Deployment & Infrastructure Topology

- **Docker Compose Orchestration:** Configured via `docker-compose.yml` (development) and `docker-compose.prod.yml` (production).
- **Container Footprint:**
  - `frontend`: Built via Multi-Stage Node 20 build; served via `nginx:1.27-alpine` (128MB RAM).
  - `backend`: Python 3.12-slim running Uvicorn on `:8000`.
  - `worker`: Python 3.12-slim running RQ `SimpleWorker(burst=True)`.
  - `chroma`: Official `chromadb/chroma:0.5.5` image on `:8000`.
- **Managed Free-Tier Backends:**
  - Neon Serverless PostgreSQL (`postgresql+asyncpg://...`).
  - Upstash Redis (`rediss://...` with TLS).
  - Groq Cloud API (`https://api.groq.com/openai/v1`).

---

# 21. Verified Current Technical Limitations

1. **In-Memory Rate Limiter:** `RateLimitMiddleware` maintains an in-memory dictionary; does not share quotas across multiple API replicas.
2. **Regex Symbol Fallback:** Non-Python languages rely on regex for symbol declarations rather than full semantic AST compiler passes.
3. **Destructive Wipe-and-Replace:** Re-analyzing a repository deletes and recreates all rows rather than performing incremental Git diffs.
4. **Single FIFO Queue:** Head-of-line blocking allows large repositories to starve small repositories.
5. **No Private Repositories:** Clones public repositories via anonymous HTTPS only.

---

# 22. Future Architecture & Roadmap Proposals `[PROPOSED]`

1. **Incremental Git Webhook Diff Analysis:** Ingest GitHub push webhooks, compute `git diff`, re-parse only changed files, and patch dependency edges dynamically.
2. **Distributed Redis Token-Bucket Rate Limiter:** Replace in-memory dictionary with Redis Lua scripts (`ZREMRANGEBYSCORE`).
3. **Queue Tiering (`queue:small`, `queue:large`):** Eliminate head-of-line blocking by routing repos based on size.
4. **SCIP / LSIF Semantic Indexing:** Introduce dedicated compiler sidecars for cross-file type resolution.

---

# 23. Senior / Staff Interview Technical Discussion Map

- **"Why did you choose a relational database for code graph data?"**
  - *Answer:* Referential integrity via cascading deletes, ACID transactional safety during bulk replacement, and atomic partial unique constraints preventing race conditions.
- **"How do you prevent worker crashes from deadlocking the queue?"**
  - *Answer:* Active worker heartbeat writes (`heartbeat_at`) coupled with an asynchronous FastAPI background task loop (`run_reaper_loop` in `backend/app/services/analysis_reaper.py`) failing wedged jobs older than 900s (and unstarted queued jobs >1800s) and clearing the partial unique index.
- **"Why use SSE instead of WebSockets?"**
  - *Answer:* Unidirectional server-to-client streaming, native HTTP/2 proxy support, and automatic browser reconnection without socket state overhead.
- **"Why the Dual-Transaction pattern in AI chat?"**
  - *Answer:* Commits user question in 5ms, drops database connection during 20s LLM stream to prevent pool starvation, commits assistant turn in second transaction.

---

# 24. Resume-Ready Technical Building Blocks

- **Database Concurrency Control:** *"Designed database-level mutual exclusion using a PostgreSQL partial unique index on active analysis jobs, eliminating duplicate execution race conditions across concurrent API replicas."*
- **Self-Healing Background Worker:** *"Architected a background worker heartbeat and asynchronous reaper loop that automatically detects crashed worker processes and recovers wedged jobs without manual intervention."*
- **High-Concurrency AI Streaming:** *"Implemented a dual-transaction lifecycle for streaming LLM responses over Server-Sent Events, isolating database connection pools and guaranteeing conversational message persistence during network drops."*
- **Graph Theory Algorithms:** *"Integrated an iterative, stack-based Tarjan's Strongly Connected Components algorithm to detect circular module dependencies in $O(V+E)$ time without recursion limits, and built an on-demand BFS reverse-dependency blast-radius engine with exponential distance decay and sigmoid risk saturation."*
- **Multi-Language AST Extraction:** *"Engineered a 3-tier parsing fallback system combining native Python AST, Tree-sitter for executable LOC and branching metrics, and Regex declarations across 10 programming languages."*

---

# 25. Source-of-Truth Governance Rules

1. **Codebase Over Documentation:** If code and documentation diverge, the running codebase is the sole source of truth.
2. **Strict Separation of Proposed vs. Implemented:** Architectural scaling designs must always carry the label `[PROPOSED / SCALING OPTION]`.
3. **Anti-Hallucination Resume Boundary:** Never claim distributed locks, Kubernetes auto-scaling, or private repo OAuth support as currently running in production.
