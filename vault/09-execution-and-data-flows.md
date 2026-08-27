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
    participant Redis as Redis (Queue & Cache)
    participant Worker as RQ Worker
    participant Engine as Analysis Engine
    participant GitHub as GitHub Git HTTPS
    participant Chroma as ChromaDB

    User->>Browser: Submit repository URL
    Browser->>API: POST /api/v1/repositories {url, branch}
    API->>API: validate_github_url(url)
    
    rect rgb(240, 248, 255)
        Note over API,DB: Transaction A: Create Repo & Job
        API->>DB: INSERT INTO repositories (status='pending')
        API->>DB: INSERT INTO analysis_jobs (status='queued')<br/>[Guarded by uq_active_job_per_repository]
        DB-->>API: job.id, repo.id
    end

    API->>Redis: queue.enqueue("worker.app.tasks.analyze_repository.run", repo_id, job_id)
    Redis-->>API: rq_job.id
    API-->>Browser: 202 Accepted {job_id, status: "queued"}
    Browser->>API: GET /api/v1/repositories/:id/events (SSE Connection)

    Worker->>Redis: SimpleWorker.work(burst=True) -> Dequeue Job
    Worker->>DB: UPDATE analysis_jobs SET status='running', started_at=now(), heartbeat_at=now()
    Worker->>DB: UPDATE repositories SET status='analyzing'

    Note over Worker,GitHub: Step 1: Sandboxed Shallow Clone
    Worker->>GitHub: git clone --depth 1 --branch ...
    GitHub-->>Worker: Cloned Git workspace (/var/lib/codesensei/workspaces/slug)

    Note over Worker,Engine: Step 2: Walk & Concurrent Parse
    Worker->>Engine: AnalysisOrchestrator.run_on_path(workspace)
    Engine->>Engine: FileWalker.walk() -> filter ignore patterns
    
    par ThreadPoolExecutor (parse_workers=4)
        Engine->>Engine: Parse file 1 (Python AST / Tree-sitter / Regex)
        Engine->>Engine: Parse file 2 (Python AST / Tree-sitter / Regex)
        Engine->>Engine: Parse file N (Python AST / Tree-sitter / Regex)
    end

    loop Every N files processed
        Worker->>DB: UPDATE analysis_jobs SET progress=X, heartbeat_at=now()
        API-->>Browser: SSE event: "progress" {progress: X, message: "..."}
    end

    Note over Engine: Step 3: Graph, Cycles & Classification
    Engine->>Engine: GraphBuilder.build() -> resolve dependency edges
    Engine->>Engine: Tarjan's SCC -> detect_cycles(edges)
    Engine->>Engine: Metric calculation & dead_code reachability
    Engine->>Engine: classify_architecture() -> Mermaid diagram
    Engine-->>Worker: RepositoryAnalysis result object

    rect rgb(245, 255, 245)
        Note over Worker,DB: Transaction B: Atomic Replace & Version Stamp
        Worker->>DB: DELETE FROM source_files WHERE repository_id = :id (Cascades)
        Worker->>DB: Batch INSERT source_files
        Worker->>DB: Batch INSERT symbols, metrics, dependencies
        Worker->>DB: UPDATE repositories SET status='ready', file_count=N, star_count=0, analysis_version=1...
        Worker->>DB: Commit Tx B
    end

    Note over Worker,Chroma: Step 4: Best-Effort Vector Indexing
    Worker->>Worker: CodeChunker.chunk_repository() (symbol-aware slices)
    Worker->>Worker: Batch call Embedding Provider (HuggingFace / Ollama)
    Worker->>Chroma: Upsert vectors & metadata to collection repo_:id
    Note over Worker,Chroma: Failure here does not fail analysis (IndexingDegraded swallowed)

    Worker->>DB: UPDATE analysis_jobs SET status='succeeded', progress=100, completed_at=now()
    Worker->>Redis: Invalidate cached graphs (delete_prefix("repo::id"))
    API-->>Browser: SSE event: "succeeded" {progress: 100}
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
    participant LLM as Groq Cloud API (Llama 3.3)

    User->>Browser: Types question + attaches context chip ("src/core/auth.py")
    Browser->>API: POST /api/v1/chat-sessions/:sessionId/chat {question, attached: [...]}

    rect rgb(255, 250, 240)
        Note over API,DB: Transaction 1: Save User Turn & Validate Access
        API->>DB: SELECT * FROM chat_sessions WHERE id = :id AND user_id = :user_id
        DB-->>API: session entity
        API->>DB: SELECT * FROM repositories WHERE id = session.repository_id
        DB-->>API: repo entity (check is_public or owner)
        API->>DB: SELECT * FROM chat_messages WHERE session_id = :id ORDER BY created_at DESC LIMIT 20
        DB-->>API: message history
        API->>DB: INSERT INTO chat_messages (session_id, role='user', content=:q, attached_context=[...])
        API->>DB: UPDATE chat_sessions SET last_activity_at = now()
        API->>DB: Commit Tx 1 (User turn is permanently stored)
    end

    Note over API,Chroma: Retrieval Step
    API->>API: Generate embedding for question
    API->>Chroma: Query collection repo_:repo_id for top-k nearest chunks
    API->>Chroma: Exact fetch chunks for attached_context ("src/core/auth.py")
    Chroma-->>API: Relevant code chunks with line ranges & symbol names

    Note over API,LLM: Prompt Synthesis & Streaming
    API->>API: build_chat_messages(system_prompt, history, retrieved_chunks, question)
    API->>LLM: POST /chat/completions {stream: true, messages: [...]}
    
    loop Token Streaming over SSE
        LLM-->>API: Token chunks
        API-->>Browser: SSE event: "token" {content: "chunk"}
    end

    API-->>Browser: SSE event: "citations" {citations: [{file, start, end, symbol}]}
    API-->>Browser: SSE event: "done"

    rect rgb(240, 255, 240)
        Note over API,DB: Transaction 2: Save Assistant Turn
        API->>DB: INSERT INTO chat_messages (session_id, role='assistant', content=accumulated_text, citations=[...])
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
    
    Reaper->>DB: UPDATE analysis_jobs SET status='failed', error='worker_timeout' WHERE status='running' AND now() - heartbeat_at > 300s RETURNING repository_id
    DB-->>Reaper: [repo_id_1, repo_id_2]
    
    Note over Reaper,DB: Unblock Repositories
    Reaper->>DB: UPDATE repositories SET status='failed', error_message='Analysis stopped responding...' WHERE id IN (repo_id_1, repo_id_2) AND status IN ('pending', 'cloning', 'analyzing')
    
    Note over DB: Partial Unique Index uq_active_job_per_repository is now cleared!
    
    Browser->>Reaper: User clicks "Retry Analysis" (POST /repositories/:id/analyze)
    Reaper->>DB: INSERT INTO analysis_jobs (status='queued') [SUCCEEDS]
```
