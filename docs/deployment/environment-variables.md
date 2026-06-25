# Environment Variables Reference

Every variable the system reads, grouped. Defaults are from `backend/app/core/config.py` /
`shared/config/defaults.py` / `.env.example`. "Required?" means the app won't function
correctly without it in the relevant mode.

> Production guards: the app refuses to boot in `APP_ENV=production` with the default
> `APP_SECRET_KEY` or default `POSTGRES_PASSWORD`, forces `secure` cookies, and disables
> mock auth + dev login.

## Application
| Var | Example | Required | Purpose / impact if missing |
| --- | --- | --- | --- |
| `APP_NAME` | CodeSensei | no | Display name |
| `APP_ENV` | development | yes | development/staging/production/test; gates prod hardening |
| `APP_LOG_LEVEL` | INFO | no | structlog level |
| `APP_DEBUG` | false | no | FastAPI debug (denied in prod) |
| `APP_SECRET_KEY` | `openssl rand -hex 32` | **yes** | JWT signing; default rejected in prod → no valid sessions |
| `APP_CORS_ORIGINS` | https://your-domain | yes (prod) | CORS allowlist; wrong value → browser blocks API calls |

## Auth (GitHub OAuth)
| Var | Example | Required | Purpose |
| --- | --- | --- | --- |
| `GITHUB_OAUTH_CLIENT_ID` / `_SECRET` | from GitHub app | yes (real login) | OAuth credentials |
| `GITHUB_OAUTH_CALLBACK_URL` | https://host/api/v1/auth/github/callback | yes (real login) | Must match the GitHub app exactly |
| `FRONTEND_BASE_URL` | https://your-domain | yes | Post-login redirect target |
| `SESSION_COOKIE_NAME` | codesensei_session | no | JWT cookie name |
| `SESSION_TTL_SECONDS` | 604800 | no | Session lifetime |
| `AUTH_DEV_LOGIN_ENABLED` | true (dev) | no | Enables `/auth/dev-login` (dev/test only) |

## Mock auth (dev/test only — disabled in prod)
| Var | Example | Purpose |
| --- | --- | --- |
| `MOCK_AUTH` | true | Auto-authenticate as a fixed user (skips GitHub) |
| `MOCK_AUTH_USERNAME` / `_EMAIL` / `_DISPLAY_NAME` / `_AVATAR_URL` / `_GITHUB_ID` | mockuser… | Mock identity |

## API
| Var | Default | Purpose |
| --- | --- | --- |
| `API_HOST` / `API_PORT` | 0.0.0.0 / 8000 | Bind |
| `API_WORKERS` | 4 (2 free-tier) | uvicorn workers |
| `API_REQUEST_TIMEOUT_SECONDS` | 120 | Request timeout |
| `API_MAX_REPO_SIZE_MB` / `API_MAX_REPO_FILES` | 500 / 5000 | Reject oversized repos |
| `API_RATE_LIMIT_PER_MINUTE` | 60–100 | Per-IP rate limit |

## PostgreSQL
| Var | Example | Required | Purpose |
| --- | --- | --- | --- |
| `POSTGRES_HOST` / `_PORT` / `_DB` / `_USER` / `_PASSWORD` | neon-host / 5432 / codesensei / … | yes | Connection |
| `POSTGRES_SSLMODE` | require (cloud) | yes (Neon) | TLS; missing → Neon refuses |
| `POSTGRES_POOL_SIZE` / `_MAX_OVERFLOW` | 10 / 20 | no | Pool sizing |

## Redis
| Var | Example | Required | Purpose |
| --- | --- | --- | --- |
| `REDIS_HOST` / `_PORT` / `_DB` / `_PASSWORD` | upstash-host / 6379 / 0 / … | yes | Queue + cache |
| `REDIS_TLS` | true (Upstash) | yes (Upstash) | TLS; missing → connection fails |
| `REDIS_QUEUE_NAME` | analysis / analysis-jobs | no | RQ queue name (backend + worker must agree) |
| `REDIS_CACHE_TTL_SECONDS` | 3600 | no | Cache TTL |

## ChromaDB
| Var | Default | Purpose |
| --- | --- | --- |
| `CHROMA_HOST` / `CHROMA_PORT` | chroma / **8000** | Vector DB (image always binds 8000) |
| `CHROMA_COLLECTION_PREFIX` | repo_ / codesensei | Per-repo collection name prefix |

## AI providers
| Var | Default | Required when | Purpose |
| --- | --- | --- | --- |
| `LLM_PROVIDER` | ollama | always | `ollama` or `groq` |
| `EMBEDDING_PROVIDER` | ollama | always | `ollama` / `huggingface` / `local` |
| `GROQ_API_KEY` | — | `LLM_PROVIDER=groq` | Groq auth |
| `GROQ_CHAT_MODEL` | llama-3.3-70b-versatile | no | Model (update if deprecated) |
| `OLLAMA_BASE_URL` / `_CHAT_MODEL` / `_EMBED_MODEL` | http://ollama:11434 / … | `*=ollama` | Local LLM/embeddings |
| `HUGGINGFACE_API_KEY` | — | `EMBEDDING_PROVIDER=huggingface` | HF auth |
| `HUGGINGFACE_EMBED_MODEL` | all-MiniLM-L6-v2 | no | Embedding model |
| `LOCAL_EMBED_MODEL` | all-MiniLM-L6-v2 | `EMBEDDING_PROVIDER=local` | CPU embeddings |
| `AI_TOP_K_CHUNKS` | 8 | no | Retrieval breadth |
| `AI_MAX_CONTEXT_TOKENS` | 8192 | no | Prompt budget |

## Worker & reaper
| Var | Default | Purpose |
| --- | --- | --- |
| `WORKER_CONCURRENCY` | 2 (1 free-tier) | Parallel jobs |
| `WORKER_JOB_TIMEOUT_SECONDS` | 1800 | Hard job timeout |
| `WORKER_RETRY_MAX_ATTEMPTS` | 3 | Retries |
| `WORKER_CLONE_DIR` | /var/lib/codesensei/workspaces | Clone location |
| `ANALYSIS_REAPER_ENABLED` | true | Enable stuck-job reaper |
| `ANALYSIS_REAPER_INTERVAL_SECONDS` | 60 | Sweep interval |
| `ANALYSIS_RUNNING_HEARTBEAT_TIMEOUT_SECONDS` | 600 | RUNNING job death threshold |
| `ANALYSIS_QUEUED_TIMEOUT_SECONDS` | 1800 | QUEUED abandon threshold |

## Observability
| Var | Default | Purpose |
| --- | --- | --- |
| `METRICS_ENABLED` / `METRICS_PORT` | true / 9100 | Prometheus |
| `TRACING_ENABLED` / `OTEL_EXPORTER_OTLP_ENDPOINT` | false / … | OpenTelemetry |

## Frontend (build-time, `VITE_` prefix)
| Var | Default | Purpose |
| --- | --- | --- |
| `VITE_API_BASE_URL` | http://localhost:8000 | Dev proxy target |
| `VITE_ENABLE_STREAMING` / `VITE_ENABLE_DARK_MODE` | true | Feature flags |
| `VITE_DEFAULT_PAGE_SIZE` / `VITE_SEARCH_DEBOUNCE` | 20 / 300 | UI tuning |

## Secrets (never commit)
`APP_SECRET_KEY`, `GITHUB_OAUTH_CLIENT_SECRET`, `GROQ_API_KEY`, `HUGGINGFACE_API_KEY`,
`POSTGRES_PASSWORD`, `REDIS_PASSWORD`.
