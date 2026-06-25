# ADR-0007: Standalone analysis engine library

**Status:** Accepted

## Context
The static-analysis logic (clone, multi-language parse, graph, metrics, dead code,
architecture) plus the RAG building blocks are the heart of the product. They must be
testable in isolation and reusable by both the worker (indexing) and the backend (chat).

## Decision
Implement them as a **standalone Python library** (`analysis-engine/`) with its own
`pyproject.toml`, depending only on `shared/`. It has **no** knowledge of FastAPI, RQ, or the
database. The worker wires it to persistence; the backend reuses its RAG components.

## Alternatives considered
- **Put the logic inside the backend** — couples parsing to the web framework, makes unit
  testing require app/infra, and blocks reuse by the worker.
- **A separate microservice** — adds network hops and ops overhead for what is fundamentally
  a pure function (bytes → analysis).

## Consequences
- (+) Pure, deterministic, fast unit tests (no infra).
- (+) Reused by worker + backend without duplication.
- (+) Could be published/run as a CLI independently.
- (−) A shared library means version discipline across consumers (handled via `shared/` and
  the monorepo).
See [../architecture/component-architecture.md](../architecture/component-architecture.md).
