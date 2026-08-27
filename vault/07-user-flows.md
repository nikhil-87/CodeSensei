# 07. Complete End-to-End User Flows

> **Status:** Codebase-grounded analysis of frontend pages, state stores, and backend endpoints.  
> **Source Verification:** [frontend/src/pages/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/pages/), [frontend/src/routes/router.tsx](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/routes/router.tsx), [frontend/src/store/nodeContextStore.ts](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/store/nodeContextStore.ts).

---

## 1. Flow Overview & Sitemap

```mermaid
flowchart TD
    Login["/login<br/>(LoginPage)"] -->|GitHub OAuth / Dev Login| Dashboard["/<br/>(RepositoryListPage)"]
    
    Dashboard -->|Submit Repo URL| SubmitModal["Submit Modal<br/>(POST /repositories)"]
    SubmitModal -->|Redirect to Events| RepoRoot["/repos/:id/overview<br/>(RepositoryDashboardPage)"]
    
    RepoRoot --> NavGraph["/repos/:id/graph<br/>(DependencyGraphPage)"]
    RepoRoot --> NavComp["/repos/:id/complexity<br/>(ComplexityPage)"]
    RepoRoot --> NavDead["/repos/:id/dead-code<br/>(DeadCodePage)"]
    RepoRoot --> NavArch["/repos/:id/architecture<br/>(ArchitecturePage)"]
    RepoRoot --> NavImp["/repos/:id/impact<br/>(ImpactAnalysisPage)"]
    RepoRoot --> NavChat["/repos/:id/chat<br/>(AIAssistantPage)"]
    
    NavGraph -->|Select Node -> Ask AI| CrossContext["nodeContextStore<br/>(Queues Context Chip)"]
    NavArch -->|Select Layer -> Ask AI| CrossContext
    CrossContext --> NavChat

    Dashboard --> Discover["/discover<br/>(DiscoverPage - Public)"]
    Discover --> RepoAnalyses["/discover/r?url=...<br/>(RepositoryAnalysesPage)"]
    Discover --> UserProfile["/u/:username<br/>(ProfilePage - Public)"]
    Dashboard --> Starred["/stars<br/>(StarredPage)"]
```

---

## 2. Major User Journeys

### Journey 1: Authentication & Onboarding
1. **Initial Visit:** Unauthenticated user navigates to `/`. The React router's `RequireAuth` guard detects no active session (`auth.me` query returns 401) and redirects to `/login`.
2. **Authentication Method:**
   - **Production:** User clicks "Sign in with GitHub". Browser redirects to `/api/v1/auth/github/login`, then to GitHub. Upon consent, GitHub redirects back to `/api/v1/auth/github/callback`. Backend verifies anti-CSRF state cookie, exchanges code, creates/updates user in PostgreSQL, sets `codesensei_session` cookie, and redirects to `/`.
   - **Development:** User fills the Dev Login form (`username`), triggering `POST /api/v1/auth/dev-login`. Backend sets session cookie and returns user object.
3. **Landing:** Browser enters `RepositoryListPage` (`/`), listing all previously submitted repositories owned by the user.

---

### Journey 2: Repository Submission & Analysis
```mermaid
sequenceDiagram
    autonumber
    actor User
    participant FE as React Frontend
    participant API as FastAPI Backend
    participant Redis as Redis Queue
    participant Worker as RQ Worker
    participant Engine as Analysis Engine
    participant DB as PostgreSQL

    User->>FE: Paste GitHub URL ("https://github.com/owner/repo")
    FE->>API: POST /api/v1/repositories {url, branch: null}
    API->>API: validate_github_url (SSRF check)
    API->>DB: Insert Repository (PENDING) + AnalysisJob (QUEUED)
    API->>Redis: Enqueue analyze_repository(repo_id, job_id)
    API-->>FE: 202 Accepted {job_id, status: "queued"}
    FE->>FE: Navigate to /repos/:id/overview
    FE->>API: GET /api/v1/repositories/:id/events (SSE)

    Worker->>Redis: Dequeue job
    Worker->>DB: Update job RUNNING + repo ANALYZING
    Worker->>API: (SSE emits event: "running", progress: 0)
    API-->>FE: SSE event: "running"

    Worker->>Worker: Git shallow clone (depth=1)
    Worker->>API: (SSE emits event: "progress", progress: 10, "clone complete")
    API-->>FE: SSE event: "progress" (10%)

    Worker->>Engine: Parse files concurrently (ThreadPoolExecutor)
    loop Every N files
        Worker->>DB: Update job.heartbeat_at & progress
        API-->>FE: SSE event: "progress" (20%..60%)
    end

    Worker->>Engine: Build Graph, Detect Cycles (Tarjan's), Metrics, Dead Code
    Worker->>DB: Atomic replace: SourceFiles, Symbols, Dependencies, Metrics
    Worker->>Worker: Symbol-aware chunking & ChromaDB vector upsert
    Worker->>DB: Update job SUCCEEDED + repo READY
    API-->>FE: SSE event: "succeeded" (100%)
    FE->>FE: Invalidate React Query caches; render Dashboard
```

---

### Journey 3: Graph Exploration & Cycle Inspection
1. **Navigation:** User navigates to `/repos/:id/graph` ([DependencyGraphPage.tsx](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/pages/DependencyGraphPage.tsx)).
2. **Data Fetching:** TanStack Query calls `GET /api/v1/repositories/:id/dependencies`. Backend checks Redis cache `repo:<id>:graph`; if missed, fetches nodes and edges from PostgreSQL, executes Tarjan's SCC to detect cycles, caches in Redis, and returns JSON.
3. **Visualization (Cytoscape.js):**
   - Files render as circular nodes colored by programming language.
   - Node size reflects lines of code (LOC).
   - Directed arrows represent file-level imports.
4. **Interactions:**
   - **Filter by Language:** User toggles language checkboxes; Cytoscape hides irrelevant nodes.
   - **Highlight Cycles:** User clicks "Highlight Cycles". The UI iterates through detected SCCs (`response.cycles`), highlighting cyclic edges in bold red.
   - **Node Inspection:** Clicking a node opens the slide-out `NodeInspector` panel displaying LOC, cyclomatic complexity, incoming/outgoing dependencies, and declared symbols.
   - **Cross-Context Queueing:** In `NodeInspector`, user clicks "Ask AI about this file". The frontend calls `nodeContextStore.attachFile(repoId, file)`, sets `pendingPrompt = "Explain what this file does and how it relates to its dependencies"`, and navigates to `/repos/:id/chat`.

---

### Journey 4: Impact Analysis (Blast Radius Calculation)
1. **Navigation:** User navigates to `/repos/:id/impact` ([ImpactAnalysisPage.tsx](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/pages/ImpactAnalysisPage.tsx)).
2. **File Selection:** User selects or searches for a target file (e.g. `backend/app/core/auth.py`) and sets maximum depth slider (1–5, default 3).
3. **Calculation:** User clicks "Analyze Impact", triggering `POST /api/v1/repositories/:id/impact`.
4. **Backend Processing (`ImpactService`):**
   - Executes upstream reverse-dependency BFS traversal starting at the target file.
   - For every reached file, computes distance-decay risk score: `risk = exp(-0.5 * (distance - 1))`.
   - Computes aggregate risk score squashed via sigmoid: `overall_risk = 1.0 - exp(-score / 8)`.
5. **Presentation:** Frontend displays a summary card with risk rating (`Low`, `Medium`, `High`, `Critical`), a list of impacted upstream files sorted by proximity and risk, and direct links to inspect each dependent file.

---

### Journey 5: Conversational AI & Context-Grounded RAG
```mermaid
sequenceDiagram
    autonumber
    actor User
    participant ChatUI as AIAssistantPage (React)
    participant Store as nodeContextStore
    participant API as FastAPI Backend
    participant Chroma as ChromaDB
    participant LLM as Groq / Ollama
    participant DB as PostgreSQL

    Note over User,ChatUI: Auto-consume cross-feature context
    ChatUI->>Store: consumePendingPrompt()
    Store-->>ChatUI: "Explain what auth.py does..." + AttachedFile[auth.py]
    
    User->>ChatUI: Click Send (or Auto-Send)
    ChatUI->>API: POST /api/v1/chat-sessions/:sessionId/chat<br/>{question, attached: [{path: "src/core/auth.py"}]}
    
    Note over API,DB: Transaction 1: Save User Turn
    API->>DB: Load chat_session (verify ownership)
    API->>DB: Load last 20 messages history
    API->>DB: Insert ChatMessage (role: "user", attached_context: [...])
    API->>DB: Commit Tx1
    
    Note over API,LLM: Retrieval & Token Streaming
    API->>Chroma: Vector search (query embedding) + Exact filter on attached paths
    Chroma-->>API: Top-k code chunks (content, line ranges, symbols)
    API->>API: Build system prompt with citations & history
    API->>LLM: Stream chat completion
    
    loop Stream Tokens
        LLM-->>API: chunk
        API-->>ChatUI: SSE event: "token" {content: "..."}
    end
    API-->>ChatUI: SSE event: "citations" {citations: [...]}
    API-->>ChatUI: SSE event: "done"
    
    Note over API,DB: Transaction 2: Save Assistant Turn
    API->>DB: Insert ChatMessage (role: "assistant", citations: [...])
    API->>DB: Commit Tx2
```

---

### Journey 6: Social Discovery, Starring & Public Sharing
1. **Public Discovery:** Any visitor navigates to `/discover` ([DiscoverPage.tsx](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/pages/DiscoverPage.tsx)). TanStack Query calls `GET /api/v1/discover/repositories`.
2. **Repository-Centric Browsing:** Repositories display as cards grouped by `(url, branch)`. The card shows total stars, primary languages, file count, and number of public analyses.
3. **Inspecting Public Analysis:** Clicking a repository card navigates to `/discover/r?url=...` ([RepositoryAnalysesPage.tsx](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/pages/RepositoryAnalysesPage.tsx)), listing every public analysis created for that repository by different users.
4. **Starring:** Authenticated users click the Star button on a card or dashboard header. The frontend sends `PUT /api/v1/repositories/:id/star`. The backend updates PostgreSQL `stars` and increments `repositories.star_count`, returning `StarState(starred=True, star_count=N)`.
5. **Public Profiles:** Clicking an analyst's username navigates to `/u/:username` ([ProfilePage.tsx](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/src/pages/ProfilePage.tsx)), showing their public portfolio and total stars received across all projects.
