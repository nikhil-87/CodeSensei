# ADR-0001: FastAPI for the backend

**Status:** Accepted

## Context
The backend must serve a REST API, stream Server-Sent Events (analysis progress + chat
tokens), validate complex request bodies, and call async I/O (DB, Redis, HTTP to LLM
providers). The team is Python-first (the analysis engine is Python).

## Decision
Use **FastAPI** (with uvicorn) as the web framework, with SQLAlchemy 2.0 async + asyncpg
for data access and Pydantic v2 for validation/serialization.

## Alternatives considered
- **Flask / Django REST** — synchronous by default; SSE + async LLM streaming would be
  awkward; Django is heavyweight for an API-only service.
- **Node/Express or Go** — would split the codebase away from the Python analysis engine,
  losing direct reuse of the engine's RAG building blocks.

## Consequences
- (+) First-class async → clean SSE streaming and concurrent I/O.
- (+) Pydantic validation + automatic OpenAPI/Swagger at `/docs`.
- (+) Same language as the engine → shared types and reuse.
- (−) Async SQLAlchemy has a steeper learning curve and sharper footguns (session scope).
- (−) Fewer "batteries included" than Django (auth/admin are hand-rolled).
