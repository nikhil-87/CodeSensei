# 09. Detailed Execution & Data Flows

> **Status:** Codebase-grounded execution traces and sequence diagrams.  
> **Source Verification:** [backend/app/services/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/app/services/), [worker/worker/app/tasks/analyze_repository.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/worker/app/tasks/analyze_repository.py), [analysis-engine/engine/orchestrator.py](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/engine/orchestrator.py).

---

## 1. Analysis Ingestion & Background Pipeline Flow

This flow represents the primary write path of the system: moving from an HTTP submission, through background queuing and shallow cloning, into multi-threaded parsing, atomic persistence, and best-effort vector indexing.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as React SPA
    participant API as FastAPI Backend
    participant DB as PostgreSQL
    participant Redis as Redis Queue and Cache
    participant Worker as RQ Worker
    participant Engine as Analysis Engine
    participant GitHub as GitHub Git HTTPS
    participant Chroma as ChromaDB

    User->>Browser: Submit repository URL
    Browser->>API: POST /api/v1/repositories
    API->>API: validate_github_url SSRF guard
    
    rect rgb(240, 248, 255)
        Note over API,DB: Transaction A: Create Repo and Job
        API->>DB: INSERT INTO repositories (status=pending)
        API->>DB: INSERT INTO analysis_jobs (status=queued)
        DB-->>API: job_id, repo_id
    end

    API->>Redis: enqueue analysis job
    Redis-->>API: rq_job_id
    API-->>Browser: 202 Accepted with job_id
    Browser->>API: GET /api/v1/repositories/{id}/events (SSE)

    Worker->>Redis: SimpleWorker burst mode dequeues job
    Worker->>DB: UPDATE analysis_jobs SET status=running, heartbeat_at=now
    Worker->>DB: UPDATE repositories SET status=analyzing

    Note over Worker,GitHub: Step 1: Sandboxed Shallow Clone
    Worker->>GitHub: git clone --depth 1 --branch
    GitHub-->>Worker: Cloned Git workspace directory

    Note over Worker,Engine: Step 2: Walk and Concurrent Parse
    Worker->>Engine: AnalysisOrchestrator.run_on_path
    Engine->>Engine: FileWalker filters ignore patterns
    
    par ThreadPoolExecutor with 4 workers
        Engine->>Engine: Parse file 1 (Python AST / Tree-sitter / Regex)
        Engine->>Engine: Parse file 2 (Python AST / Tree-sitter / Regex)
        Engine->>Engine: Parse file N (Python AST / Tree-sitter / Regex)
    end

    loop Every N files processed
        Worker->>DB: UPDATE analysis_jobs SET progress=X, heartbeat_at=now
        API-->>Browser: SSE event: progress
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
    API-->>Browser: SSE event: succeeded
    Browser->>Browser: Render Complete Dashboard
```

---

## 2. Persistent RAG Streaming Execution Flow (Dual-Transaction Pattern)

This flow details how the platform handles multi-second LLM streaming without holding long-lived database transactions open, ensuring user turns are never rolled back if clients disconnect.

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Browser as React Chat UI
    participant API as FastAPI (ChatSessionService)
    participant DB as PostgreSQL
    participant Chroma as ChromaDB
    participant LLM as Groq Cloud API

    User->>Browser: Types question and attaches context chip for auth.py
    Browser->>API: POST /api/v1/chat-sessions/{sessionId}/chat with question

    rect rgb(255, 250, 240)
        Note over API,DB: Transaction 1: Save User Turn and Validate Access
        API->>DB: SELECT from chat_sessions WHERE id = session_id
        DB-->>API: session entity
        API->>DB: SELECT from repositories WHERE id = session.repository_id
        DB-->>API: repo entity (check is_public or owner)
        API->>DB: SELECT from chat_messages WHERE session_id = id LIMIT 20
        DB-->>API: message history
        API->>DB: INSERT INTO chat_messages (role=user)
        API->>DB: UPDATE chat_sessions SET last_activity_at = now()
        API->>DB: Commit Tx 1 (User turn is permanently stored)
    end

    Note over API,Chroma: Retrieval Step
    API->>API: Generate embedding for question
    API->>Chroma: Query collection for top-k nearest chunks
    API->>Chroma: Exact fetch chunks for attached context auth.py
    Chroma-->>API: Relevant code chunks with line ranges and symbols

    Note over API,LLM: Prompt Synthesis and Streaming
    API->>API: build_chat_messages with system prompt, history, chunks
    API->>LLM: POST /chat/completions with stream=true
    
    loop Token Streaming over SSE
        LLM-->>API: Token chunks
        API-->>Browser: SSE event: token
    end

    API-->>Browser: SSE event: citations
    API-->>Browser: SSE event: done

    rect rgb(240, 255, 240)
        Note over API,DB: Transaction 2: Save Assistant Turn
        API->>DB: INSERT INTO chat_messages (role=assistant, citations=...)
        API->>DB: Commit Tx 2 (Assistant turn is permanently stored)
    end
```

---

## 3. Synchronous vs. Asynchronous Work Separation

To preserve high API responsiveness, the architecture enforces a strict divide between synchronous request/response operations and asynchronous background processing:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      SYNCHRONOUS (FastAPI API Layer)                    │
│  - Request validation & SSRF URL checks (< 2ms)                         │
│  - Database lookups & cached reads (< 10ms)                             │
│  - Tarjan's SCC cycle detection on cached graphs (< 15ms)               │
│  - Impact analysis reverse BFS walk (< 25ms)                            │
│  - Enqueueing analysis jobs into Redis (< 5ms)                          │
│  - Token streaming over SSE (Long-lived connection, zero worker blocking)│
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Redis Queue (Job ID)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      ASYNCHRONOUS (RQ Worker Layer)                     │
│  - Shallow Git cloning over network (2s - 60s)                          │
│  - Filesystem tree walking & binary decoding (100ms - 5s)               │
│  - Concurrently parsing source files via ThreadPoolExecutor (1s - 30s)  │
│  - Resolving imports into dependency edges (200ms - 2s)                 │
│  - Batch PostgreSQL deletion & re-insertion (500ms - 3s)                │
│  - Code chunking & embedding generation (2s - 45s)                      │
│  - ChromaDB vector upsertion (500ms - 5s)                               │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Stuck-Job Reaper Flow (Crash Recovery)

If an analysis worker dies unexpectedly (OOM kill, host termination, or network partition during git clone), the repository would remain stuck in `ANALYZING` and the active job in `RUNNING`. The `AnalysisReaper` recovers the system automatically:

```mermaid
sequenceDiagram
    autonumber
    participant Lifespan as FastAPI Lifespan Loop
    participant Reaper as AnalysisReaper Task
    participant DB as PostgreSQL
    participant Browser as Client Browser

    Note over Lifespan: Reaper runs every 30 seconds
    Lifespan->>Reaper: Trigger reap_stale_jobs(settings)
    
    Reaper->>DB: UPDATE analysis_jobs SET status=failed WHERE status=running AND heartbeat_at > 300s
    DB-->>Reaper: repo_ids
    
    Note over Reaper,DB: Unblock Repositories
    Reaper->>DB: UPDATE repositories SET status=failed WHERE id IN repo_ids
    
    Note over DB: Partial Unique Index uq_active_job_per_repository is now cleared!
    
    Browser->>Reaper: User clicks Retry Analysis
    Reaper->>DB: INSERT INTO analysis_jobs status=queued succeeds
```
