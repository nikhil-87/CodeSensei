# 17. Testing Architecture & Verification Strategy

> **Status:** Codebase-grounded analysis of test suites, harnesses, mocks, and CI execution.  
> **Source Verification:** [backend/tests/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/backend/tests/), [worker/tests/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/worker/tests/), [analysis-engine/tests/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/analysis-engine/tests/), [frontend/tests/e2e/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/frontend/tests/e2e/), [tests/contract/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/tests/contract/), [tests/load/](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/tests/load/), [.github/workflows/ci.yml](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/.github/workflows/ci.yml).

---

## 1. Test Pyramid & Directory Topology

```
                  ┌───────────────────────────────┐
                  │          E2E Tests            │
                  │   Playwright (1 spec file)    │
                  │  frontend/tests/e2e/*.spec.ts │
                  └───────────────┬───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │    Contract & Load Tests      │
                  │  tests/contract/ (OpenAPI)    │
                  │   tests/load/ (Locustfile)    │
                  └───────────────┬───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │      Integration Tests        │
                  │ backend/tests/integration/    │
                  │  worker/tests/test_tasks.py   │
                  │ (Postgres 16, fakeredis, RQ)  │
                  └───────────────┬───────────────┘
                                  │
                  ┌───────────────┴───────────────┐
                  │          Unit Tests           │
                  │ analysis-engine/tests/ (AST)  │
                  │ backend/tests/unit/ (Config)  │
                  │  frontend/src/**/*.test.tsx   │
                  └───────────────────────────────┘
```

---

## 2. Test Suite Breakdown

### 2.1 Unit Tests

#### A. Analysis Engine (`analysis-engine/tests/`)
- **Focus:** Hermetic testing of static parsing, graph generation, cycle detection, and dead code heuristics.
- **Dependencies:** Pure Python. Zero external network or database calls.
- **Key Test Files:**
  - `test_python_parser.py`: Verifies AST parsing of functions, classes, async definitions, and import variations.
  - `test_tree_sitter_parser.py`: Validates LOC and branch complexity counting across TypeScript, Go, Java, and C++.
  - `test_graph_builder.py`: Asserts correct directed edge generation between modules.
  - `test_cycles.py`: Validates Tarjan's SCC cycle detection against known cyclic graph topologies (2-cycles, 3-cycles, disjoint cycles).
  - `test_dead_code.py`: Verifies reachability confidence scores for used vs unused symbols.
  - `test_chunker.py`: Validates symbol-aware code chunking boundary alignment and line overlaps.

#### B. Backend Unit (`backend/tests/unit/`)
- **Focus:** Security sanitization, JWT token encoding/decoding, configuration parsing.
- **Key Test Files:**
  - `test_security.py`: Tests `validate_github_url` (rejects HTTP, IP addresses, credentials, query strings) and `safe_join` (asserts `PathTraversalError` on `../../` or backslashes).
  - `test_auth.py`: Tests HS256 JWT minting, expiration timestamp assertions, and claims extraction.

#### C. Frontend Unit (`frontend/src/`)
- **Focus:** Vitest component tests testing rendering, user actions, and store behavior.
- **Command:** `npm run test:coverage`.

---

### 2.2 Integration Tests

#### A. Backend Integration (`backend/tests/integration/`)
- **Focus:** Full FastAPI endpoint execution with real PostgreSQL and Redis service containers.
- **Harness:** `pytest-asyncio`, `httpx.AsyncClient`, and Alembic migration runner.
- **Database Strategy:** Executes real migrations (`0001` through `0007`) against a disposable test database (`codesensei_test`). Each test function executes in a clean transaction or truncated schema.
- **Key Suites:**
  - `test_auth_api.py`: Tests login redirects, cookie setting, `/api/v1/auth/me`, and logout.
  - `test_repositories_api.py`: Tests repo creation, listing, duplicate submit conflict (409), visibility toggle, and cascade deletion.
  - `test_insights_api.py`: Tests `/dependencies`, `/complexity`, `/dead-code`, and `/impact` endpoints.
  - `test_health_api.py`: Asserts 200 OK on `/healthz` and verifies deep dependency probes on `/readyz`.

#### B. Worker Integration (`worker/tests/`)
- **Focus:** Background task execution (`analyze_repository.run`), database persistence, and heartbeat updates.
- **Mocking Strategy:**
  - Redis is mocked using `fakeredis`, allowing in-memory RQ job enqueueing without a live Redis server.
  - PostgreSQL is tested using the real test database.
  - Git cloning is exercised against local fixtures or mocked Git repositories.

---

### 2.3 Contract Tests (`tests/contract/`)
- **File:** `tests/contract/test_openapi_contract.py`.
- **Purpose:** Asserts that the live FastAPI application's generated OpenAPI 3.1 schema matches expectations:
  - Validates that all defined routes are mounted under `/api/v1/`.
  - Asserts that request models and response models conform to Pydantic v2 schemas.
  - Ensures breaking changes to API contracts are caught in CI before deployment.

---

### 2.4 Load Tests (`tests/load/`)
- **File:** `tests/load/locustfile.py`.
- **Tool:** Locust (Python-based distributed load testing framework).
- **Simulated Scenarios:**
  - 80% Read traffic: Browsing Discover hub (`/discover/repositories`), reading dependency graphs, and fetching complexity rankings.
  - 15% Interactive traffic: Asking questions in AI chat sessions.
  - 5% Write traffic: Submitting new repository URLs for analysis.

---

### 2.5 End-to-End (E2E) Tests (`frontend/tests/e2e/`)
- **Tool:** Playwright (`@playwright/test`).
- **File:** `repository-flow.spec.ts`.
- **Workflow Tested:**
  1. Opens frontend at `http://localhost:5173`.
  2. Authenticates via Dev Login form.
  3. Submits a GitHub repository URL.
  4. Waits for SSE progress bar to transition from `queued` -> `running` -> `succeeded`.
  5. Asserts navigation to Overview dashboard and verifies metrics cards render.
  6. Navigates to Dependency Graph page and verifies Cytoscape canvas renders nodes.

---

## 3. Mocking Strategy & Fixture Analysis

| Subsystem | Unit Tests | Integration Tests | E2E Tests |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | None (No DB) | **Real** (Postgres 16 container) | **Real** (Postgres 16 container) |
| **Redis** | None | **Mocked** (`fakeredis`) | **Real** (Redis 7 container) |
| **ChromaDB** | Mocked in-memory | Mocked client / Degraded fallback | **Real** ChromaDB container |
| **Groq / LLM** | Mocked stream generator | Mocked streaming generator | Real (or recorded mock) |
| **HuggingFace**| Deterministic dense vector | Fake embeddings (384 floats) | Real (or local model) |
| **Git Repos** | Local filesystem folders | Local fixtures / git bare repos | Public GitHub repositories |

---

## 4. Test Execution Reality & CI Pipeline

### 4.1 CI Workflow (`.github/workflows/ci.yml`)
The GitHub Actions workflow runs on `ubuntu-latest` and orchestrates:
1. **Change Detection (`detect-changes`):** Uses `dorny/paths-filter` to skip irrelevant jobs.
2. **Linting (`lint-python`, `lint-frontend`):** Ruff 0.6.9 for Python; ESLint + TypeScript `tsc --noEmit` for Frontend.
3. **Analysis Engine Tests:** Runs `pytest --cov=engine` with Python 3.12.
4. **Backend Tests:** Spins up service containers for `postgres:16-alpine` and `redis:7-alpine`, installs editable dependencies, and runs `pytest --cov=app`.
5. **Worker Tests:** Runs `pytest` using `fakeredis`.
6. **Frontend Tests:** Runs `npm ci` and `npm run test:coverage` with Node 20.
7. **Docker Matrix Builds:** Builds container images for `backend`, `worker`, and `frontend` using Buildx to guarantee Dockerfiles compile cleanly.
8. **Security Scans:** Executes Aqua Security's Trivy vulnerability scanner on container images.

### 4.2 Local Developer Reality
- **Host Execution Note:** Running `pytest` directly on a developer host requires Python 3.12 with development dependencies installed (`pip install -e ".[dev]"`). Pre-existing virtual environments (`.venv`) with hardcoded paths from other machines fail.
- **Recommended Execution:** Use Docker Compose:
  ```bash
  docker compose run --rm backend pytest
  docker compose run --rm worker pytest
  ```
