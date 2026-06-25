# LLD Interview Questions & Answers

### "How is the backend structured (class/layer design)?"
Four layers with a strict dependency direction: **Router → Service → Repository → ORM
Model**. Routers are thin (validate via Pydantic, call one service, shape output) and never
write SQL. Services hold all business logic and never import FastAPI, so they're unit-testable
without HTTP. Repositories encapsulate queries behind a generic `BaseRepository` plus
domain-specific methods. A DI container (`core/dependencies.py`) assembles
session→repository→service per request via `Annotated[T, Depends(...)]`.

### "Walk me through the database design."
11 tables, UUID PKs, timestamp mixins. `users` 1:N `repositories` 1:N `source_files` 1:N
`symbols`; `source_files` 1:1 `metrics` and N:M-ish `dependencies` (from/to file). Social:
`stars` (unique per user/repo, denormalized `star_count`). AI: `chat_sessions` 1:N
`chat_messages` (JSONB citations + attached context). Invariants are enforced with
constraints: `uq_repositories_owner_id_url_branch`, `uq_stars_user_repository`, and the
partial `uq_active_job_per_repository`. Cascade deletes keep the graph consistent. Full
schema: [../database/schema.md](../database/schema.md).

### "How would you design the API for analysis (async work)?"
`POST /repositories/{id}/analyze` returns `202` with an `AnalysisJobRead` immediately and
enqueues the job; clients poll progress via an SSE stream `GET /…/events`. This separates
"accepted" from "done", keeps the request fast, and the `202`/SSE pattern is the standard for
long-running work. Duplicate submits get `409` from the DB invariant.

### "How does the dependency graph get built (LLD)?"
Each parser emits a uniform `FileAnalysis` (symbols + imports). The graph builder resolves
each import target to a concrete file via relative-path, module-path, then fuzzy
bare-name matching, producing `DependencyEdge`s; a separate pass detects cycles. Persisted as
`dependencies` rows with a unique `(from,to,kind,symbol)` edge constraint to dedupe. The
frontend turns these into an adjacency model (`graphModel.ts`) for traversal, clustering, and
impact math.

### "How does the analysis pipeline persist results safely?"
In one transaction the worker deletes the repo's `source_files` (cascading to
symbols/metrics/dependencies) and inserts the fresh rows, then updates cached stats + version
stamps. Re-analysis is therefore atomic — never half-old/half-new. Vector chunks upsert by a
stable `chunk_id`, so re-indexing is idempotent too.

### "How do you stream chat tokens (LLD)?"
`ChatSessionService.stream_chat` is an async generator yielding dict events. It loads history,
saves the user turn, retrieves chunks (guaranteeing tagged files), prompts the LLM, and yields
`token` events as they arrive, then a de-duplicated numbered `citations` event, then `done`
(saving the assistant turn). FastAPI wraps it as `text/event-stream`. The frontend's
POST-capable SSE client parses the frames.

### "How is dependency injection done without a framework container?"
FastAPI's `Depends` is the container. Factory functions build each layer and are composed via
`Annotated` type aliases (`RepositoryServiceDep`, etc.). Request scope = session scope; the
session is created per request and disposed after. Auth deps (`CurrentUserDep`,
`OptionalUserDep`) decode the cookie and load the user; `verify_repository_access` is a
side-effecting dependency for read authorization.

### "How do you compute impact/criticality?"
Pure graph math in `graphModel.computeImpact`: BFS over the adjacency to get transitive
dependents (impact scope) and dependencies (reach), longest chains (depth), and a 0–100
criticality blending direct fan-in, transitive reach share, and hub-ness, mapped to a
Low/Moderate/High/Critical label. Same function powers both the impact page and the graph
inspector.

### "How do you keep services testable?"
They depend on repository *interfaces* (constructor-injected) and contain no HTTP or SQL.
Tests construct a service with a test-DB-backed repository (or a fake) and assert behavior —
no app server needed. See [../testing/README.md](../testing/README.md).
