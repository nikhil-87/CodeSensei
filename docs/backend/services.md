# Backend Services

Business logic lives in `backend/app/services/`. Services never import FastAPI and never
write raw SQL (they call repositories), which keeps them unit-testable.

| Service | File | Key methods | Responsibility |
| --- | --- | --- | --- |
| `RepositoryService` | `repository_service.py` | `submit`, `get_for_user`, `list`, `list_public`, `list_public_grouped`, `public_repository_group`, `delete`, `set_visibility`, `to_read_model(s)`, `to_read_models_with_stars` | Repo lifecycle, access control, read-model mapping + freshness; raises `409` on duplicate submit |
| `AnalysisService` | `analysis_service.py` | `trigger`, `get_job`, `latest_job_for_repository`, `list_jobs`, `poll_until_terminal` | Create jobs, enqueue, status, SSE polling |
| `AIService` | `ai_service.py` | `stream_chat`, `delete_repository_index`, `_build_runtime` | Stateless RAG chat + ChromaDB cleanup |
| `ChatSessionService` | `chat_session_service.py` | `create_session`, `list_sessions`, `get_session`, `rename_session`, `delete_session`, `list_messages`, `stream_chat` | Persistent conversations; auto-saves user + assistant turns with citations |
| `DependencyService` | `dependency_service.py` | `get_graph` | Build `DependencyGraphResponse` (+ cache) |
| `MetricService` | `metric_service.py` | `complexity_ranking` | Rank files by complexity |
| `DeadCodeService` | `dead_code_service.py` | `report` | Unused-symbol report |
| `ImpactService` | `impact_service.py` | `analyze` | Change blast-radius |
| `ArchitectureService` | `architecture_service.py` | `report` | Layer/component discovery + Mermaid |
| `DocumentationService` | `documentation_service.py` | `generate` | AI-generated README / onboarding docs |
| `StarService` | `star_service.py` | `star`, `unstar`, `is_starred`, `starred_ids`, `list_starred` | Idempotent stars + denormalized count |
| `ProfileService` | `profile_service.py` | `get_profile`, `list_public_repositories` | Public profiles |
| `AuthService` | `auth_service.py` | `new_state`, `authorize_url`, `exchange_code` | GitHub OAuth (state → code → token → profile → upsert) |
| `analysis_reaper` (module) | `analysis_reaper.py` | `reap_stale_jobs`, `run_reaper_loop` | Crash recovery loop (runs in app lifespan) |

## Notable behaviors

### `RepositoryService.submit`
Validates the GitHub URL (`core/security.validate_github_url` — SSRF guard), normalizes
it, creates the `repositories` row (`PENDING`) and an `analysis_jobs` row (`QUEUED`) in one
transaction, then asks `JobDispatcher` to enqueue. Returns `(Repository, AnalysisJob)`. The
unique active-job index means a concurrent submit/analyze surfaces as `409`.

### `AIService.stream_chat`
Lazily builds an `AIRuntime` for the repo (provider clients + Chroma store), retrieves
top-k chunks (guaranteeing slots for any tagged `attached_paths`), builds the prompt, and
yields SSE dict events (`token`, `citations`, `done`, `error`). It is **stateless** — no
DB writes.

### `ChatSessionService.stream_chat`
Same retrieval+LLM core, but **stateful**: loads prior messages for context, saves the
user turn before streaming and the assistant turn (with citations + attached context)
after, and bumps `last_activity_at`. Enforces session ownership.

### `StarService.star` / `unstar`
Idempotent (insert-or-ignore / delete-if-exists) and updates the denormalized
`repositories.star_count`. Returns the new count so the UI can reconcile optimistic state
(this is what fixed an earlier star-count race).

### `analysis_reaper`
`reap_stale_jobs(settings)` finds `RUNNING` jobs with a stale `heartbeat_at` (older than
`ANALYSIS_RUNNING_HEARTBEAT_TIMEOUT_SECONDS`) and `QUEUED` jobs older than
`ANALYSIS_QUEUED_TIMEOUT_SECONDS`, marks them `FAILED`, and flips their repos from
`PENDING/CLONING/ANALYZING` → `FAILED`. `run_reaper_loop` does an immediate startup sweep
(clearing orphans left by a crash) then repeats every `ANALYSIS_REAPER_INTERVAL_SECONDS`.
