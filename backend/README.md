# Backend — FastAPI REST + SSE API

The synchronous edge of the platform. Receives repository submissions, enqueues
analysis jobs, serves analysis results from Postgres, proxies AI chat requests
to the configured LLM provider (Groq cloud or local Ollama, with RAG context
from ChromaDB), and streams progress events over SSE.

## Layout (Clean Architecture)

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/
│   │       │   ├── repositories.py    # POST /repos, GET /repos, GET /repos/{id}
│   │       │   ├── analysis.py        # POST /repos/{id}/analyze, GET status
│   │       │   ├── dependencies.py    # GET dependency graph
│   │       │   ├── dead_code.py       # GET dead code report
│   │       │   ├── complexity.py      # GET complexity rankings
│   │       │   ├── impact.py          # POST impact analysis
│   │       │   ├── architecture.py    # GET architecture diagrams
│   │       │   ├── documentation.py   # POST documentation generation
│   │       │   ├── ai.py              # POST chat, GET chat stream (SSE)
│   │       │   └── health.py          # /healthz, /readyz, /metrics
│   │       └── router.py              # APIRouter aggregator
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings (12-factor)
│   │   ├── logging.py                 # structlog JSON config
│   │   ├── security.py                # URL validation, path-traversal guards
│   │   ├── exceptions.py              # Domain + HTTP exception mapping
│   │   ├── middleware.py              # Request ID, timing, CORS, rate-limit
│   │   └── dependencies.py            # FastAPI Depends() providers
│   ├── db/
│   │   ├── base.py                    # SQLAlchemy DeclarativeBase
│   │   ├── session.py                 # async engine + session factory
│   │   └── seed.py                    # dev seed data
│   ├── models/                        # SQLAlchemy ORM models
│   ├── schemas/                       # Pydantic DTOs
│   ├── repositories/                  # Persistence layer (Repository Pattern)
│   ├── services/                      # Business logic (Service Layer)
│   ├── workers/                       # RQ job enqueue helpers (consumer in /worker)
│   ├── cache/                         # Redis cache utilities
│   ├── observability/                 # Prometheus metrics, OTel tracing
│   └── main.py                        # FastAPI app factory + lifespan
├── alembic/                           # DB migrations
│   ├── env.py
│   └── versions/
├── tests/
│   ├── unit/
│   ├── integration/
│   └── conftest.py
├── pyproject.toml                     # PEP 621 metadata + tool config
├── requirements.txt                   # Pinned runtime deps (generated)
├── Dockerfile                         # Multi-stage slim Python 3.12
└── .env.example
```

## Layering rules

| Layer        | May import from                | Must not import                       |
| ------------ | ------------------------------ | ------------------------------------- |
| `api/`       | `services/`, `schemas/`, `core/` | `repositories/`, `models/` (directly) |
| `services/`  | `repositories/`, `schemas/`, `core/` | `api/`                          |
| `repositories/` | `models/`, `db/`            | `services/`, `api/`                   |
| `models/`    | (only SQLAlchemy)              | everything else                       |

Enforced via `import-linter` config in `pyproject.toml`.

## Run

```bash
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs at `http://localhost:8000/docs`.
