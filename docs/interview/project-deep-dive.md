# Project Deep Dive

A complete, interview-ready walkthrough. Read this once and you can talk about the system
for 45 minutes.

## 1. What it is (one breath)
A GitHub repository intelligence platform: submit a public repo → it's cloned, statically
analyzed (dependency graph, complexity, dead code, architecture, impact), indexed into a
vector DB, and made conversational — you ask questions and an LLM answers with citations via
RAG. Built as a real distributed system on free infrastructure.

## 2. The components and why each exists
- **Frontend (React SPA)** — visualizations (Cytoscape graph, Recharts, Mermaid) + chat.
  Stateless; talks only to `/api/v1`; consumes two SSE streams.
- **Backend (FastAPI, async)** — auth, validation, authorization, CRUD, enqueues jobs,
  serves analyses, runs RAG chat, runs the reaper. Stateless.
- **Worker (RQ)** — does the slow work off the request path: clone → analyze → persist →
  index.
- **Analysis engine (standalone lib)** — the pure parsing/graph/RAG logic; reused by worker
  and backend; unit-testable without infra.
- **PostgreSQL** — system of record (relational analysis data + JSONB citations).
- **Redis** — RQ queue + cache.
- **ChromaDB** — per-repo vector collections for retrieval.
- **Groq / HuggingFace** — free-tier LLM + embeddings; swappable to Ollama/local by env.

## 3. The write path (analysis) — the distributed-systems story
1. `POST /repositories` validates the URL (SSRF guard), creates a repo (`PENDING`) + job
   (`QUEUED`) in one transaction, enqueues `analyze_repository(repo_id, job_id)`, returns
   `202`.
2. The **unique active-job partial index** means a duplicate "Analyze" returns `409` — no
   double work.
3. The worker marks the job `RUNNING` + writes a **heartbeat**, clones depth-1, runs the
   engine pipeline (clone→walk→parse→graph→metrics→dead-code→architecture), and **atomically
   replaces** the repo's rows (delete + insert in one transaction).
4. It then **best-effort indexes** chunks into ChromaDB; if embeddings/Chroma are down it
   raises `IndexingDegraded` and the job still **SUCCEEDS** (structural analysis is valuable
   alone).
5. If the worker dies mid-job, the heartbeat goes stale and a background **reaper** fails the
   job + repo so the user can retry.
6. The frontend watches progress over **SSE** (`/events`).

> This is the part interviewers care about: a queue, a worker, idempotent re-analysis,
> at-least-once delivery handled with a DB invariant + a reaper, and graceful degradation.

## 4. The read path (RAG chat) — the AI story
1. `POST /chat-sessions/{id}/chat` (SSE). Ownership is checked; prior turns load for context.
2. The question is embedded and used to **retrieve top-k chunks** from the repo's Chroma
   collection. Files the user **tagged** (e.g. from the graph inspector) get **guaranteed
   slots**.
3. A prompt is built (system + retrieved context with file/line provenance + history) and
   streamed through the LLM.
4. Tokens stream to the client; **numbered citations** are emitted and the assistant turn is
   persisted (content + citations + attached context).

## 5. The "intelligence" surfaces
- **Dependency graph** with directional highlighting (who depends on this vs. what this
  depends on), focus mode with depth, cycles, and a rich inspector (impact, criticality,
  code structure, usage).
- **Architecture** view (layers + Mermaid).
- **Complexity / dead code / impact** read-models.
- **"Ask AI about this node"** ties the graph to chat by tagging the file.

## 6. Cross-cutting engineering
- **Auth**: GitHub OAuth → httpOnly JWT cookie; mock auth in dev.
- **Security**: SSRF URL validation, IDOR checks, path-traversal guards, rate limiting.
- **Config**: ~60 env vars, Pydantic settings, production hardening, provider portability.
- **Observability**: Prometheus, structlog, OpenTelemetry-ready.
- **CI**: change-filtered lint/test/build/security across all services.

## 7. What I'd do next (shows direction)
Symbol/call-level graph; retrieval re-ranking; incremental re-analysis; move rate-limiting to
Redis for multi-replica correctness; pgvector consolidation at scale.

## 8. The honest limitations (own them)
File/import-level graph (not per-function calls); free-tier LLM/embedding rate limits and
quality; single-node Chroma; analysis is a point-in-time snapshot. See
[tradeoffs.md](tradeoffs.md).
