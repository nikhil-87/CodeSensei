# Testing Strategy

## Philosophy
Tests are **hermetic** (no live external services), fast, and focused on the layers that
hold business logic. The type system (strict TS, Pydantic, mypy) is treated as the first
line of testing — a lot of correctness is enforced at build time.

## Test layers

| Layer | Tooling | Scope |
| --- | --- | --- |
| Analysis engine | `pytest` (`analysis-engine/tests/`) | Parsers, graph builder, cycles, chunker — pure logic, no infra |
| Backend | `pytest` (`backend/tests/`) | Services + repositories against a test DB; API via `httpx`/TestClient |
| Worker | `pytest` (`worker/tests/`) | Task orchestration, persistence, progress mapping |
| Frontend unit | `vitest` + Testing Library (`happy-dom`) | Components, hooks, `graphModel` math |
| Frontend E2E | `playwright` | Critical user flows in a real browser |

## CI gates (`.github/workflows/ci.yml`)
A `detect-changes` job (`dorny/paths-filter`) skips unaffected suites, then runs:
`lint-python` (ruff, mypy), `lint-frontend` (ESLint **0 warnings**, Prettier), `test-engine`,
`test-backend` (needs Postgres + Redis services), `test-worker`, `test-frontend`
(Playwright), then `docker-build` (matrix) and `security-scan`. Python 3.12, Node 20.
`codeql.yml` runs weekly SAST; `release.yml` publishes images on tags.

## What's well covered
- Analysis engine logic (parsing/graph/chunking) — the highest-value, most deterministic
  code.
- Backend service behavior and access control.
- `graphModel.ts` pure functions (adjacency, reachability, impact).
- Strict type checks (TS `strict` + `noUncheckedIndexedAccess`; Pydantic v2; mypy).

## What's intentionally lighter (honest)
- No live LLM/embedding calls in tests — providers are stubbed; RAG quality is validated
  manually.
- ChromaDB interactions are exercised via the worker path, not exhaustively unit-tested.
- E2E covers happy paths of the core flows, not every page permutation.

## Running tests
```bash
# Engine
cd analysis-engine && pytest

# Backend (needs a test Postgres + Redis; CI provides them)
cd backend && pytest

# Worker
cd worker && pytest

# Frontend unit + E2E
cd frontend && npm run test
cd frontend && npm run test:e2e
```

## Manual verification used during development
Because the embedded browser can't screenshot Cytoscape's accelerated canvas, graph
correctness is verified programmatically via the live `cy` instance (zoom, node
`renderedPosition`, classes) and responsive layout via measured `scrollWidth` vs
`innerWidth` across viewports. This pattern is documented in
[../troubleshooting/README.md](../troubleshooting/README.md).
