# HLD Interview Questions & Answers

Concise, defensible answers to common high-level-design questions about this project.

### "Walk me through the architecture."
A React SPA talks to a stateless FastAPI backend over `/api/v1`. The backend owns auth,
validation, authorization, and CRUD, and serves analysis read-models. Slow work (cloning +
multi-language parsing + embedding) is pushed to a background **RQ worker** via **Redis**.
The worker drives a standalone **analysis engine** library, persists structured results to
**PostgreSQL**, and indexes code chunks into **ChromaDB**. AI chat is **RAG**: retrieve
top-k chunks from Chroma, prompt **Groq**, stream tokens + citations back over SSE. Postgres
is the system of record; Redis is queue+cache; Chroma is the vector store. Everything runs on
free tiers.

### "Why this architecture / why a worker and queue?"
Analysis can take tens of seconds to minutes and must not block the API or tie up request
workers. A queue decouples submission from processing, lets me scale workers independently,
and survives restarts. It also gives a natural place to enforce "one analysis per repo at a
time."

### "How does analysis work end to end?"
Validate URL → create repo+job rows + enqueue (202) → worker clones depth-1 → engine parses
each file (Python AST / tree-sitter / regex fallback) → builds the import graph + metrics +
dead code + architecture → atomically replaces the repo's rows in Postgres → chunks + embeds
+ upserts to Chroma → marks the job succeeded. Progress streams to the UI via SSE; a heartbeat
+ reaper handle crashes.

### "How does AI chat work?"
RAG. At index time the worker chunks code (symbol-aware) and stores embeddings per repo. At
query time the backend embeds the question, retrieves the top-k most similar chunks
(guaranteeing slots for user-tagged files), builds a grounded prompt, and streams the LLM's
answer with numbered citations that map back to file/line ranges.

### "How do you handle large repositories?"
Size/file caps (`API_MAX_REPO_SIZE_MB`, `API_MAX_REPO_FILES`) reject the extreme cases;
clone is depth-1; parsing is parallelized; the graph UI clusters folders and supports focus
mode + depth limits so huge graphs stay legible; per-repo vector collections keep retrieval
fast. Indexing is best-effort so a partial AI index never fails the structural analysis.

### "How do you prevent duplicate analyses?"
A **partial unique index** on `analysis_jobs(repository_id, status) WHERE status IN
('queued','running')`. A second enqueue violates it and the API returns `409` — the DB, not
just app logic, guarantees one active job per repo.

### "How do you handle worker failures?"
Every progress update writes `heartbeat_at`. A background **reaper** (in the API lifespan)
fails jobs whose heartbeat is stale or that sat queued too long, and flips their repos to
`FAILED` so users can retry. An immediate startup sweep clears orphans from a crash.

### "How do you handle authorization?"
Identity comes from a verified httpOnly JWT cookie. Owned resources require ownership;
readable resources are owner-or-public; everything else returns `404` (not `403`) to avoid
leaking existence. A `verify_repository_access` dependency centralizes the repo read check.

### "Where are the bottlenecks and how do you scale?"
API: add stateless replicas (move rate-limit to Redis). Analysis: add workers. Retrieval:
per-repo collections + eventually pgvector/managed vector DB. DB: pooling now, read replicas
later. LLM: provider is swappable; paid tier or queueing raises limits. See
[scalability.md](scalability.md).

### "What happens if the LLM/embeddings provider is down?"
Indexing failures are caught (`IndexingDegraded`) and don't fail analysis. Chat surfaces an
error event. Providers are env-swappable, so I can fail over to Ollama/local without code
changes.

### "Why SSE instead of WebSockets?"
The two streams (analysis progress, chat tokens) are **server→client only**. SSE is simpler,
works over plain HTTP, auto-reconnects, and needs no extra protocol. I added a small
POST-capable SSE client on the frontend for the chat body.
