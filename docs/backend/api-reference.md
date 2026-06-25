# Backend API Reference

Base URL: **`/api/v1`**. Auth is via the httpOnly cookie `codesensei_session` (JWT HS256).
"Required" = `CurrentUserDep`; "Optional" = `OptionalUserDep`; "Repo access" =
`verify_repository_access` (owner or public, else `404`).

> Source of truth: `backend/app/api/v1/endpoints/*.py`. The live OpenAPI/Swagger UI is at
> `/docs` on the running backend.

## Health & observability — `health.py`
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| GET | `/healthz` | Liveness (always 200) | None |
| GET | `/readyz` | Readiness (checks Postgres + Redis) | None |
| GET | `/metrics` | Prometheus metrics | None |

## Authentication — `auth.py`
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| GET | `/auth/github/login` | Redirect to GitHub consent (sets anti-CSRF state cookie) | None |
| GET | `/auth/github/callback` | OAuth callback → upsert user → set session cookie | None |
| GET | `/auth/me` | Current user | Required |
| POST | `/auth/logout` | Clear session cookie | Required |
| POST | `/auth/dev-login` | Password-less dev login (dev/test only) | None |

## Repositories — `repositories.py`
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| POST | `/repositories` | Submit a repo → `202` + job. Re-submitting a repo you already analyzed returns `409 repository_already_exists` (with the existing `repository_id`); if one is already analyzing, `409 analysis_already_running`. Never creates a duplicate row. | Required |
| GET | `/repositories` | List my repos (paginated, filter by status) | Required |
| GET | `/repositories/{repository_id}` | Get one repo (owner or public) | Optional |
| PATCH | `/repositories/{repository_id}/visibility` | Toggle `is_public` | Required (owner) |
| DELETE | `/repositories/{repository_id}` | Delete repo + all analysis + vector index | Required (owner) |

## Analysis jobs — `analysis.py`
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| POST | `/repositories/{repository_id}/analyze` | Re-trigger analysis → `202` (or `409` if active) | Repo access |
| GET | `/repositories/{repository_id}/jobs` | List recent jobs | Repo access |
| GET | `/repositories/{repository_id}/jobs/latest` | Latest job | Repo access |
| GET | `/repositories/{repository_id}/events` | **SSE** progress stream | Repo access |

## Discovery — `discover.py`
Repository-centric: a `(url, branch)` repository may have many public analyses by different
users; Discover lists the **repository** once, and a second endpoint lists its analyses.
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| GET | `/discover/repositories` | Browse public repositories — one card per `(url, branch)` group (search, sort, paginate). Items are `DiscoverRepositoryRead` (`analyses_count`, `total_stars`, `latest_repository_id`, …). | Optional |
| GET | `/discover/repository?url=&branch=` | One repository's public analyses (the overview / history page) → `RepositoryGroupDetail` with a header + a `PublicAnalysisRead[]` (each with analyst, date, version, freshness). | Optional |

## Chat sessions — `chat_sessions.py`
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| POST | `/repositories/{repository_id}/chat-sessions` | Create session | Required |
| GET | `/repositories/{repository_id}/chat-sessions` | List my sessions for repo | Required |
| GET | `/chat-sessions/{session_id}` | Get session | Required (owner) |
| PATCH | `/chat-sessions/{session_id}` | Rename | Required (owner) |
| DELETE | `/chat-sessions/{session_id}` | Delete | Required (owner) |
| GET | `/chat-sessions/{session_id}/messages` | List messages | Required (owner) |
| POST | `/chat-sessions/{session_id}/chat` | **SSE** send + stream answer (auto-saves turns) | Required (owner) |

## AI (stateless) — `ai.py`
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| POST | `/ai/chat` | **SSE** stateless RAG chat | Optional (repo read) |

## Code analysis reads
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| GET | `/repositories/{repository_id}/dependencies` | Dependency graph | Repo access |
| GET | `/repositories/{repository_id}/complexity` | Complexity ranking (`?top_n`) | Repo access |
| GET | `/repositories/{repository_id}/dead-code` | Unused symbols | Repo access |
| POST | `/repositories/{repository_id}/impact` | Change blast-radius | Repo access |
| GET | `/repositories/{repository_id}/architecture` | Layers + Mermaid | Repo access |
| POST | `/repositories/{repository_id}/documentation` | Generated docs | Repo access |

## Stars — `stars.py`
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| PUT | `/repositories/{repository_id}/star` | Star (idempotent) | Required |
| DELETE | `/repositories/{repository_id}/star` | Unstar | Required |
| GET | `/me/stars` | My starred repos | Required |

## Profiles — `users.py`
| Method | Path | Summary | Auth |
| --- | --- | --- | --- |
| GET | `/users/{username}` | Public profile | Optional |
| GET | `/users/{username}/repositories` | User's public repos | Optional |

## Conventions
- **Pagination:** `?page=&page_size=` → `{items, total, page, page_size}`.
- **Errors:** `{detail}`; `404` for not-found *and* forbidden (avoids existence leaks);
  `409` for duplicate active job; `429` when rate-limited (`Retry-After`).
- **SSE:** `Content-Type: text/event-stream`, framed `event: <name>\ndata: <json>\n\n`.
