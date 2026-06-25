# Data Lifecycle & Query Patterns

How data is created, mutated, read, and deleted across the system.

## Lifecycle by entity

| Entity | Created | Updated | Deleted |
| --- | --- | --- | --- |
| `users` | first GitHub OAuth (or mock auth) | profile fields on each login | cascade when user deleted (admin-only path) |
| `repositories` | `POST /repositories` | status transitions, cached stats, version stamps after each analysis | `DELETE /repositories/{id}` (owner) → cascades + Chroma collection drop |
| `analysis_jobs` | submit/analyze | worker progress + heartbeat; reaper on stale | cascade with repo |
| `source_files`/`symbols`/`metrics`/`dependencies` | worker persistence | replaced wholesale on re-analysis | cascade with repo / replaced |
| `stars` | `PUT …/star` | — (idempotent) | `DELETE …/star` or cascade |
| `chat_sessions` | `POST …/chat-sessions` | rename, `last_activity_at` on new message | `DELETE` (owner) or cascade with repo/user |
| `chat_messages` | each chat turn (user + assistant) | — (immutable) | cascade with session |

## Re-analysis is destructive-then-rebuild (atomic)

On every successful re-analysis the worker, in one transaction:
1. deletes the repo's `source_files` (cascades to symbols/metrics/dependencies),
2. inserts the fresh rows,
3. updates the `repositories` cached stats + stamps.

This guarantees the graph is never half-old/half-new. The vector index is **upserted** by
stable `chunk_id`, so re-indexing the same repo is also idempotent.

## Hot query patterns

| Query | Indexes used | Where |
| --- | --- | --- |
| List my repos by status | `repositories(owner_id)`, `status` | `RepositoryService.list` |
| Public discovery (grouped by `(url, branch)`; sort by stars/recent/name, search) | `repositories(url, branch, star_count)`, `owner`, window funcs | `RepositoryService.list_public_grouped` |
| Repository overview (all public analyses of one repo) | `repositories(url, branch, is_public, status)`, `owner` | `RepositoryService.public_repository_group` |
| Dependency graph for a repo | `source_files(repository_id)`, `dependencies(from/to)` | `DependencyService.get_graph` |
| Complexity ranking | `metrics(cyclomatic)` | `MetricService.complexity_ranking` |
| Dead code | `symbols(is_used)` | `DeadCodeService.report` |
| List my chat sessions for a repo | `ix_chat_sessions_user_repo_activity` | `ChatSessionService.list_sessions` |
| Star count / starred set | `uq_stars_user_repository`, `stars(user_id)` | `StarService` |

## Privacy & isolation
- All "my" lists filter by `owner_id`/`user_id` from the authenticated cookie — never from
  a client-supplied id.
- Chat sessions/messages are strictly per-user; ownership is re-checked on every
  session-scoped route.
- Repo reads allow the owner *or* anyone if `is_public`; everything else is `404`.
- On repository delete, the Chroma collection `repo_<id>` is dropped so embedded code does
  not linger.

## Caching
- Redis caches some analysis read-models (TTL `REDIS_CACHE_TTL_SECONDS`).
- The frontend caches with TanStack Query (`staleTime` 1 min for most, 5 min for
  insights). Mutations invalidate the relevant query keys.
