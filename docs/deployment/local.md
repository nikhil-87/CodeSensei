# Local Development Setup (from zero)

This guide assumes you have never seen the project. It gets you to a fully working local
instance with Docker Compose.

## Prerequisites

| Tool | Why | Install |
| --- | --- | --- |
| **Git** | clone the repo | https://git-scm.com |
| **Docker** + **Docker Compose** | run all services | https://docs.docker.com/get-docker/ |
| **Node.js 20** (optional) | frontend dev outside Docker | https://nodejs.org |
| **Python 3.12** (optional) | backend/engine dev outside Docker | https://python.org |
| An IDE | VS Code recommended | |

Accounts you may need (all free): a **GitHub OAuth app** (for real login),
**Groq** (LLM), **HuggingFace** (embeddings). For pure local dev you can skip OAuth (use
mock auth) and run Ollama instead of Groq.

## 1. Clone

```bash
git clone <your-fork-or-repo-url> github-repo-intelligence-platform
cd github-repo-intelligence-platform
```

## 2. Create the environment file

```bash
cp .env.example .env
```
Edit `.env`. The fastest "just works locally" setup:
```dotenv
APP_ENV=development
APP_SECRET_KEY=dev-secret-please-change-32-characters-min
MOCK_AUTH=true                # skip GitHub OAuth in dev
LLM_PROVIDER=groq             # or "ollama" if you run Ollama
EMBEDDING_PROVIDER=huggingface # or "local" / "ollama"
GROQ_API_KEY=gsk_...          # from console.groq.com
HUGGINGFACE_API_KEY=hf_...    # from huggingface.co/settings/tokens
```
Full reference: [environment-variables.md](environment-variables.md). OAuth setup (if you
want real login): [../development/README.md](../development/README.md).

## 3. Start services

```bash
# Free-tier shape (Groq + HuggingFace; Postgres/Redis/Chroma in containers)
docker compose -f docker/docker-compose.free-tier.yml --env-file .env up -d --build
```
This builds and starts **frontend** (`:3000`), **backend** (`:8000`), **worker**, and
**chroma**. (The free-tier file expects Postgres/Redis either as containers or external —
see the compose file and `.env`.)

## 4. Run migrations

```bash
docker exec codesensei-backend alembic upgrade head
```

## 5. Verify

```bash
docker ps --filter "name=codesensei" --format "{{.Names}} {{.Status}}"
curl -s http://localhost:3000/ | head -n1          # frontend serves
curl -s http://localhost:8000/api/v1/auth/me        # backend responds (200 with mock auth)
```
Then open http://localhost:3000, add a small public repo, and watch the analysis progress.

## First-time verification checklist
- [ ] Frontend loads at `:3000`
- [ ] `GET /api/v1/auth/me` returns 200 (mock auth) or you can complete GitHub login
- [ ] Submitting a repo creates a job and the progress bar advances
- [ ] Dependency graph renders and auto-fits
- [ ] Complexity/dead-code/architecture pages load
- [ ] AI chat streams an answer with citations (requires Groq + HuggingFace keys + a
      successful index)
- [ ] Worker logs show clone → analyze → persist → index
- [ ] `alembic current` shows `0007`

## Frontend-only dev (hot reload)
```bash
cd frontend
npm install
npm run dev          # Vite at :5173, proxies /api to :8000
```

## Troubleshooting
See [../troubleshooting/README.md](../troubleshooting/README.md). Common: Chroma must stay
on port 8000; the backend doesn't auto-migrate; PowerShell mangles inline JSON for curl
(write the body to a temp file).
