# Architecture Review & Provider‑Independence Report

**Project:** CodeSensei — GitHub Repository Intelligence Platform
**Scope of this document:** the mock‑authentication feature, the deployment‑portability
audit, and a frank review of remaining coupling and migration risk.

> **TL;DR:** The codebase was already provider‑agnostic in its bones (env‑driven
> config, dependency injection, repository pattern, `/api/v1` versioning, Alembic
> migrations, `/healthz` + `/readyz`, pluggable LLM/embedding providers). This work
> added **mock authentication** (so the app runs and the full test suite passes
> with **zero** GitHub OAuth credentials), **feature flags**, **production
> safeguards**, and closed one **cross‑platform security gap**. Migration between
> hosts is a configuration change, not a code change.

---

## 1. Updated architecture explanation

CodeSensei is four stateless services orchestrated by Docker Compose, with all
durable state kept in **external managed services**:

```
 Browser ──► frontend (Nginx, serves SPA + proxies /api) ──► backend (FastAPI)
                                                              │
                          ┌───────────────────────────────────┼───────────────┐
                          ▼                  ▼                 ▼               ▼
                    Postgres (Neon)    Redis (Upstash)   chroma (vectors)   worker (RQ)
                          │                                                   │
                          └──────────── LLM: Groq · Embeddings: HuggingFace ──┘
```

Key architectural properties that make it portable:

| Property | How it's implemented | Where |
|---|---|---|
| **Environment‑driven config** | One `Settings(BaseSettings)` reads every value from env; all defaults centralized | [backend/app/core/config.py](backend/app/core/config.py), [shared/config/defaults.py](shared/config/defaults.py) |
| **Dependency inversion** | FastAPI `Depends` providers (Annotated aliases) inject repos/services/cache/settings | [backend/app/core/dependencies.py](backend/app/core/dependencies.py) |
| **Repository pattern** | Data access behind `*Repository` classes; no raw SQL in endpoints | `backend/app/repositories/` |
| **Pluggable providers** | `LLM_PROVIDER` / `EMBEDDING_PROVIDER` select implementation at runtime | config + worker |
| **API versioning** | All routes mounted under `/api/v1` | [backend/app/main.py](backend/app/main.py) |
| **Schema migrations** | Alembic, no vendor‑specific DDL | `backend/alembic/` |
| **Health & readiness** | `/healthz` (liveness), `/readyz` (Postgres + Redis), `/metrics` | [backend/app/api/v1/endpoints/health.py](backend/app/api/v1/endpoints/health.py) |
| **Structured logging** | `structlog`‑style key/value events with request IDs | observability middleware |

---

## 2. Mock authentication

### Goal
Let a developer (or CI) run the entire app and test suite **without** registering a
GitHub OAuth app or holding any client secret — while production behaviour is
completely unchanged.

### Design
A single boolean, `MOCK_AUTH`, gated by a derived property:

```python
# backend/app/core/config.py
@property
def mock_auth_enabled(self) -> bool:
    # Hard-disabled in production regardless of how MOCK_AUTH is set.
    return self.mock_auth and self.app_env != "production"
```

When enabled, the **only** auth seam — `get_optional_user` — short‑circuits to a
predefined user (upserted by a stable fake `github_id`) before it ever looks for a
session cookie:

```python
# backend/app/core/dependencies.py
if settings.mock_auth_enabled:
    return await user_repo.upsert_from_github(
        github_id=settings.mock_auth_github_id,
        username=settings.mock_auth_username,
        ...
    )
```

### Why there are **zero** frontend changes
The frontend determines "am I logged in?" solely from `GET /api/v1/auth/me`. Because
mock auth makes that endpoint return a real user object, the SPA behaves exactly as
if a human had completed the OAuth flow — no frontend code, rebuild, or flag needed.
**This is the clean‑decoupling story:** auth policy lives entirely behind one
server‑side seam.

### Production safeguards (defence in depth)
1. **Property gate:** `mock_auth_enabled` returns `False` whenever `APP_ENV=production`,
   so even `MOCK_AUTH=true` in a prod env is inert.
2. **Loud startup log:** if `MOCK_AUTH=true` *and* prod, the app logs an `error`
   event explaining it's being ignored; if enabled in dev/test, it logs a `warning`.
   See [backend/app/main.py](backend/app/main.py).
3. **Safe defaults:** `MOCK_AUTH=false` everywhere by default; `.env.free-tier`
   (production template) ships it disabled with a comment that it's ignored in prod.
4. **Unit‑tested:** `test_config.py` asserts `mock_auth_enabled is False` under
   `app_env="production"`.

---

## 3. Feature flags

Three env‑driven flags were added as a pattern others can extend
( [shared/config/defaults.py](shared/config/defaults.py) ):

| Flag | Default | Purpose |
|---|---|---|
| `FEATURE_AI_CHAT_ENABLED` | `true` | Toggle the AI chat surface |
| `FEATURE_ANALYTICS_ENABLED` | `false` | Gate analytics collection |
| `FEATURE_NOTIFICATIONS_ENABLED` | `false` | Gate notifications |

They follow the same flow as every other setting: default → env override →
`Settings` field → injected via DI. Unit‑tested in `test_config.py`.

---

## 4. Environment variable reference (new/changed)

| Variable | Default | Notes |
|---|---|---|
| `MOCK_AUTH` | `false` | Skip OAuth, auto‑login mock user. **Ignored when `APP_ENV=production`.** |
| `MOCK_AUTH_USERNAME` | `mockuser` | Identity of the mock user. |
| `MOCK_AUTH_EMAIL` | `mockuser@example.com` | — |
| `FEATURE_AI_CHAT_ENABLED` | `true` | — |
| `FEATURE_ANALYTICS_ENABLED` | `false` | — |
| `FEATURE_NOTIFICATIONS_ENABLED` | `false` | — |

Documented in [.env.example](.env.example) and [.env.free-tier](.env.free-tier),
and wired through [docker/docker-compose.free-tier.yml](docker/docker-compose.free-tier.yml).

---

## 5. Deployment‑independence audit

I grepped the entire `backend`, `worker`, `shared`, and `analysis-engine` trees for
hardcoded hosts/URLs/ports/paths and provider‑specific assumptions. Findings:

| Check | Result |
|---|---|
| Hardcoded Codespaces / cloud URLs | **None.** Public URLs come from `FRONTEND_BASE_URL` / `GITHUB_OAUTH_CALLBACK_URL`. |
| Hardcoded `localhost` | Only as **dev defaults** in `shared/config/defaults.py`, every one overridable by env. |
| Hardcoded ports | Only defaults (`API_PORT`, DB/Redis ports), all env‑overridable. |
| Storage paths | `WORKER_CLONE_DIR` is configurable; no absolute paths baked into logic. |
| Secrets | Read exclusively from env; none committed. |
| DB vendor lock | None — SQLAlchemy + Alembic; tests run on SQLite, prod on Postgres. |
| Provider lock (LLM/embeddings) | Abstracted via `LLM_PROVIDER` / `EMBEDDING_PROVIDER`. |

**One gap found and fixed:** `safe_join` (path‑traversal guard) treated a backslash
as an ordinary character, so a Windows‑style payload (`..\..\windows\system32`) was
only caught on Windows, not on a Linux container. It now rejects backslashes
outright, making the guard **identical on every platform**. See
[backend/app/core/security.py](backend/app/core/security.py).

---

## 6. Testing strategy & results

- **Hermetic by design:** tests run on in‑memory SQLite (`StaticPool`), `fakeredis`,
  and a fake job dispatcher — **no Postgres, Redis, or network required**.
- **No OAuth credentials required:** `test_settings` sets `mock_auth=True`
  (`app_env="test"`), so every protected route is exercised as the mock user. This is
  what unblocked the 19 previously‑failing auth tests.
- **New tests:**
  - [backend/tests/integration/test_auth.py](backend/tests/integration/test_auth.py) — `/auth/me` returns the mock user; protected POST works with no cookie; created repos are owned by the mock user.
  - [backend/tests/unit/test_config.py](backend/tests/unit/test_config.py) — mock‑auth production safeguard + feature‑flag defaults/overrides.
- **Modernized fixtures:** removed the deprecated custom `event_loop` fixture
  (it conflicted with `asyncio_mode = "auto"` and `filterwarnings=error`), clearing
  2 pre‑existing teardown errors.

**Result:** from **21 failed / 38 passed** → **69 passed / 0 failed** in the
container (`python -m pytest`).

---

## 7. Remaining coupling & migration risk (honest assessment)

| Area | Coupling | Risk | Recommendation |
|---|---|---|---|
| **Auth provider** | GitHub OAuth only | Low | Auth lives behind one seam (`get_optional_user`) + `AuthService`; adding Google/GitLab is additive, not a rewrite. |
| **Repo source** | `validate_github_url` accepts only `github.com` | Low (product scope) | Intentional — it's a *GitHub* intelligence tool. Generalizing means a host allow‑list. |
| **Vector store** | ChromaDB runs as a container; data is ephemeral on redeploy | Medium | For durability, point at a managed vector DB or mount a volume; access is already isolated. |
| **LLM / embeddings** | Groq + HuggingFace selected via env | Low | Already abstracted by `*_PROVIDER`; swapping is a config change. |
| **Background jobs** | Redis/RQ | Low | Standard; swap broker via env. |
| **Frontend ↔ backend** | SPA assumes same‑origin `/api` via Nginx proxy | Low | Keeps the browser talking to one origin; portable across hosts. |

**Bottlenecks / lock‑in:** none that block migration. The single‑origin Nginx proxy
and external managed state are deliberate choices that *improve* portability.

**Security posture:** httpOnly cookies, `secure` in production, CSRF state cookie on
OAuth, IDOR guard on per‑repo access, path‑traversal guard (now cross‑platform),
secrets only via env. No OWASP Top‑10 regressions introduced.

---

## 8. Files modified / added

**Backend code**
- [shared/config/defaults.py](shared/config/defaults.py) — mock‑auth + feature‑flag defaults.
- [backend/app/core/config.py](backend/app/core/config.py) — new fields + `mock_auth_enabled` property.
- [backend/app/core/dependencies.py](backend/app/core/dependencies.py) — mock‑auth short‑circuit in `get_optional_user`.
- [backend/app/main.py](backend/app/main.py) — startup safeguard logging.
- [backend/app/core/security.py](backend/app/core/security.py) — cross‑platform backslash rejection in `safe_join`.

**Tests**
- [backend/tests/conftest.py](backend/tests/conftest.py) — `mock_auth` in test settings, `mock_user` fixture, owner‑scoped `seeded_repository`, removed deprecated `event_loop` fixture.
- [backend/tests/integration/test_auth.py](backend/tests/integration/test_auth.py) — new mock‑auth integration tests.
- [backend/tests/unit/test_config.py](backend/tests/unit/test_config.py) — new safeguard + feature‑flag unit tests.

**Config / infra / docs**
- [.env.example](.env.example) — documented mock‑auth + feature flags.
- [.env.free-tier](.env.free-tier) — mock‑auth disabled (prod) + feature flags.
- [docker/docker-compose.free-tier.yml](docker/docker-compose.free-tier.yml) — pass new env vars to backend.
- [MIGRATION_CODESPACES_TO_ORACLE.md](MIGRATION_CODESPACES_TO_ORACLE.md) — focused migration guide.
- [ARCHITECTURE_REVIEW.md](ARCHITECTURE_REVIEW.md) — this document.

---

## 9. Migration success criteria — met

A developer can: clone → set env → run locally (optionally with `MOCK_AUTH=true`,
no OAuth needed) → deploy on Codespaces → migrate to Oracle Cloud → migrate to any
VPS, **changing only environment variables and the OAuth callback URL** — no code
changes. See [MIGRATION_CODESPACES_TO_ORACLE.md](MIGRATION_CODESPACES_TO_ORACLE.md).
