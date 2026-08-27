# 18. Deployment & Infrastructure Architecture

> **Status:** Codebase-grounded infrastructure documentation based on Dockerfiles, Compose specs, and CI/CD pipelines.  
> **Source Verification:** [docker/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/docker/), [.github/workflows/ci.yml](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/.github/workflows/ci.yml), [backend/Dockerfile](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/Dockerfile), [frontend/Dockerfile](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/Dockerfile).

---

## 1. Container Packaging & Multi-Stage Builds

The platform packages its four services into isolated Docker images:

### 1.1 Backend Container (`backend/Dockerfile`)
- **Base Image:** `python:3.12-slim`.
- **Packaging:** Installs `libpq-dev` and build tools; installs `backend` and `shared` packages in non-editable mode.
- **Security:** Runs as a dedicated non-root user (`codesensei:codesensei`, UID 10001).
- **Execution:** Runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **Healthcheck:** `curl -f http://localhost:8000/healthz`.

### 1.2 Worker Container (`worker/Dockerfile`)
- **Base Image:** `python:3.12-slim`.
- **Packaging:** Multi-package context from repo root; installs `shared`, `analysis-engine`, and `worker`. Installs `git` CLI for shallow cloning.
- **Security:** Runs as non-root user (`codesensei:codesensei`); requires read/write permissions on `/var/lib/codesensei/workspaces`.
- **Execution:** Runs `python -m worker.app`.

### 1.3 Frontend Container (`frontend/Dockerfile`)
- **Multi-Stage Build:**
  - **Stage 1 (Builder):** `node:20-alpine`. Runs `npm ci`, sets `VITE_API_BASE_URL`, and executes `npm run build` to generate static assets in `/app/dist`.
  - **Stage 2 (Runtime):** `nginx:1.27-alpine`. Copies compiled `/app/dist` static assets into `/usr/share/nginx/html`.
- **Configuration:** Custom `nginx.conf` listening on port `:8080` (non-root compatible). Proxies `/api/v1/*` to the backend container while serving SPA assets with HTML5 client-side routing fallback (`try_files $uri $uri/ /index.html`).
- **Healthcheck:** `wget -q -O - http://127.0.0.1:8080/healthz`.

---

## 2. Docker Compose Deployment Topologies

The repository provides five distinct Docker Compose manifests tailored to different environments:

```
docker/
├── docker-compose.yml              # Base self-contained local stack
├── docker-compose.free-tier.yml    # Zero-cost cloud VM stack (Neon + Upstash + Groq)
├── docker-compose.dev.yml          # Developer overlay (Hot reload & volume mounts)
├── docker-compose.prod.yml         # Production hardening overlay (Resource limits & logs)
└── docker-compose.observability.yml # Prometheus + Grafana telemetry stack
```

### 2.1 Base Compose (`docker-compose.yml`)
- **Use Case:** Self-contained local evaluation where all services run locally in Docker.
- **Services:** `postgres` (16-alpine), `redis` (7-alpine), `chroma` (0.5.5), `ollama` (latest), `backend`, `worker`, `frontend`.
- **Networks:** Two isolated bridge networks:
  - `internal`: For inter-service database and queue communication.
  - `observability`: For Prometheus metrics scraping.

### 2.2 Free-Tier Cloud Compose (`docker-compose.free-tier.yml`)
- **Use Case:** Zero-cost production deployment on minimal cloud VMs (e.g. 1GB–4GB RAM Oracle Always Free Ampere A1 instance).
- **Optimization:** Removes containerized PostgreSQL and Redis; connects to external managed serverless providers:
  - PostgreSQL: External Neon Serverless database (`POSTGRES_HOST=*.neon.tech`, `POSTGRES_SSLMODE=require`).
  - Redis: External Upstash Redis (`REDIS_HOST=*.upstash.io`, `REDIS_TLS=true`).
  - LLM: Groq Cloud API (`GROQ_CHAT_MODEL=llama-3.3-70b-versatile`).
  - Embeddings: HuggingFace Serverless Inference API (`all-MiniLM-L6-v2`).
- **Strict Memory Limits:**
  - `backend`: 512MB RAM cap.
  - `worker`: 1024MB RAM cap.
  - `chroma`: 512MB RAM cap.
  - `frontend`: 128MB RAM cap.

### 2.3 Development Overlay (`docker-compose.dev.yml`)
- **Usage:** `docker compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up`
- **Features:** Mounts host source directories (`backend/app`, `worker/worker`, `analysis-engine/engine`, `frontend/src`) into containers.
- **Hot Reloading:** Uvicorn runs with `--reload`; Vite development server runs with live HMR on `:5173`.
- **Dev Backdoors Enabled:** `AUTH_DEV_LOGIN_ENABLED=true`, `MOCK_AUTH=true`.

---

## 3. Environment Configuration & Profiles

Configuration is managed through environment variables loaded via Pydantic `BaseSettings`:

| Variable Name | Default / Example | Classification | Purpose |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `development` / `production` | Core | Gates debug endpoints, CORS origins, cookie security. |
| `APP_SECRET_KEY` | *(Must be set in prod)* | **Critical Secret**| Signs session JWT tokens and HMAC state cookies. |
| `APP_CORS_ORIGINS` | `http://localhost:5173` | Security | Allowed origins for cross-origin browser requests. |
| `POSTGRES_HOST` | `localhost` / `*.neon.tech` | Database | Relational database hostname. |
| `POSTGRES_PASSWORD` | *(Must be set)* | **Critical Secret**| Relational database password. |
| `REDIS_HOST` | `localhost` / `*.upstash.io` | Queue/Cache | Redis host for RQ queue and cache. |
| `REDIS_PASSWORD` | *(Optional for local)* | Secret | Redis authentication password. |
| `REDIS_TLS` | `false` / `true` | Network | Enforces TLS connection on Redis (required for Upstash). |
| `GITHUB_OAUTH_CLIENT_ID` | *(OAuth App ID)* | Integration | GitHub OAuth 2.0 application client identifier. |
| `GITHUB_OAUTH_CLIENT_SECRET`| *(OAuth Secret)* | **Critical Secret**| GitHub OAuth client secret for token exchange. |
| `GROQ_API_KEY` | `gsk_...` | **Critical Secret**| API key for Groq Cloud LLM completions. |
| `HUGGINGFACE_API_KEY` | `hf_...` | Secret | API key for HuggingFace Inference embeddings. |
| `CHROMA_HOST` | `chroma` / `localhost` | Vector DB | Standalone ChromaDB hostname. |
| `CHROMA_PORT` | `8000` | Vector DB | ChromaDB HTTP listening port. |
| `SESSION_TTL_SECONDS` | `604800` (7 days) | Auth | Expiration lifetime for session cookies. |
| `AUTH_DEV_LOGIN_ENABLED` | `false` (in prod) | Security | Enables `/api/v1/auth/dev-login` for passwordless dev. |

---

## 4. Database Migrations in Deployment Pipeline

- **Tool:** Alembic.
- **Location:** `backend/alembic/`.
- **Migration Strategy:** Migrations execute as a discrete deployment step prior to launching the new API and worker containers.
- **Execution Command:**
  ```bash
  alembic -c backend/alembic.ini upgrade head
  ```
- **Forward-Only Migrations:** All 7 migrations (`0001` through `0007`) are additive and backward-compatible with the immediately preceding application version, allowing zero-downtime rolling updates.

---

## 5. CI/CD Pipelines (.github/workflows/)

The platform defines three automated GitHub Actions workflows:

1. **`ci.yml` (Continuous Integration):**
   - Triggers on pull requests and pushes to `main`.
   - Executes change detection, Ruff linting, frontend linting/typechecks, Pytest suites with coverage reporting, Vitest frontend coverage, Docker Buildx image builds, and Trivy security scans.
2. **`codeql.yml` (Security Scanning):**
   - Runs GitHub CodeQL advanced static analysis on Python and TypeScript codebases to detect injection and taint-tracking vulnerabilities.
3. **`release.yml` (Release Automation):**
   - Triggers on git version tags (`v*.*.*`).
   - Builds production Docker images, tags with semantic version and git SHA, and publishes to GitHub Container Registry (GHCR).
