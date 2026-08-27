# Flow Diagrams

## Authentication (GitHub OAuth)

```mermaid
sequenceDiagram
  autonumber
  participant U as User
  participant FE as Frontend
  participant BE as Backend
  participant GH as GitHub
  U->>FE: Click "Sign in"
  FE->>BE: GET /auth/github/login
  BE-->>U: 302 to GitHub consent (state cookie)
  U->>GH: Approve
  GH-->>BE: GET /auth/github/callback?code&state
  BE->>BE: verify state; exchange code to token
  BE->>GH: GET /user profile
  BE->>BE: upsert user; mint JWT
  BE-->>U: Set httpOnly cookie; 302 to frontend
  FE->>BE: GET /auth/me to fetch user
```

## Repository analysis (write path)

```mermaid
sequenceDiagram
  autonumber
  participant FE as Frontend
  participant BE as Backend
  participant PG as Postgres
  participant Q as Redis
  participant W as Worker
  participant AE as Engine
  participant CH as ChromaDB
  FE->>BE: POST /repositories (or /analyze)
  BE->>BE: validate_github_url (SSRF guard)
  BE->>PG: repo(PENDING) + job(QUEUED) [unique active-job index]
  BE->>Q: enqueue analyze_repository(repo_id, job_id)
  BE-->>FE: 202 job
  FE->>BE: GET /repositories/{id}/events (SSE)
  W->>Q: dequeue
  W->>PG: job RUNNING + repo ANALYZING + heartbeat_at
  W->>AE: clone + parse + graph + metrics + dead-code + architecture
  AE-->>W: RepositoryAnalysis
  W->>PG: atomic replace files/symbols/deps/metrics + stamps
  W->>CH: chunk + embed + upsert (repo_<id>)  [best-effort]
  W->>PG: job SUCCEEDED + repo READY
  BE-->>FE: SSE progress... succeeded
```

## AI chat (RAG, read path)

```mermaid
sequenceDiagram
  autonumber
  participant FE as Frontend
  participant BE as Backend
  participant PG as Postgres
  participant CH as ChromaDB
  participant LLM as Groq/Ollama
  FE->>BE: POST /chat-sessions/{id}/chat {question, attached_paths} (SSE)
  BE->>PG: check ownership; load history; save user turn
  BE->>CH: embed question to top-k chunks (+ tagged files guaranteed)
  BE->>LLM: prompt(system + context + history)
  LLM-->>BE: token stream
  BE-->>FE: SSE token...
  BE-->>FE: SSE citations (numbered, deduped)
  BE->>PG: save assistant turn + citations + attached_context
  BE-->>FE: SSE done
```

## Analysis job state machine

```mermaid
stateDiagram-v2
  [*] --> QUEUED
  QUEUED --> RUNNING: worker picks up
  QUEUED --> FAILED: queued timeout (reaper)
  RUNNING --> SUCCEEDED: persisted (+ indexed best-effort)
  RUNNING --> FAILED: exception OR stale heartbeat (reaper)
  RUNNING --> CANCELLED: cancel
  SUCCEEDED --> [*]
  FAILED --> [*]
  CANCELLED --> [*]
```

## Repository status

```mermaid
stateDiagram-v2
  [*] --> PENDING
  PENDING --> CLONING
  CLONING --> ANALYZING
  ANALYZING --> READY
  PENDING --> FAILED
  CLONING --> FAILED
  ANALYZING --> FAILED
  READY --> ANALYZING: re-analyze
  FAILED --> ANALYZING: retry
```

## Core user journey

```mermaid
journey
  title CodeSensei
  section Onboard
    Sign in (GitHub/mock): 5: User
    Add a repo: 5: User
    Watch analysis (SSE): 4: User
  section Explore
    Dashboard + insights: 5: User
    Dependency graph + inspector: 5: User
  section Ask
    Tag a file, ask AI: 5: User
    Read answer + citations: 5: User
  section Share
    Make public, star, profile: 4: User
```
