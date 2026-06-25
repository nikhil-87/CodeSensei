# Executive Summary

## What CodeSensei is

CodeSensei is a **GitHub repository intelligence platform**. A user submits a public
GitHub repository URL; the system clones it, statically analyses the code, and produces:

- a **dependency graph** (file → file import edges, with cycle detection),
- **complexity metrics** (cyclomatic, cognitive, LOC, function/class counts),
- **dead-code detection** (unused symbols with confidence scores),
- an **architecture view** (files grouped into layers, rendered as a Mermaid diagram),
- **impact analysis** (change blast-radius / criticality for any file),
- and a **conversational AI assistant** that answers natural-language questions about
  the codebase, grounded in the actual source via Retrieval-Augmented Generation (RAG)
  with inline file citations.

It is a portfolio-grade, production-shaped system that runs entirely on **free tiers**
(Groq for the LLM, HuggingFace for embeddings, Neon for Postgres, Upstash for Redis,
Oracle Cloud Free Tier for compute).

## The 30-second pitch

> "CodeSensei turns any GitHub repo into an explorable knowledge base. It runs a
> multi-language static-analysis pipeline in a background worker, stores the structured
> results in Postgres, indexes the code into a vector database, and lets you *ask
> questions* about the codebase that are answered by an LLM grounded in the real source
> with citations. It's a full distributed system — API, async worker, queue, vector
> store, and SPA — built to run on zero-cost infrastructure."

## Business value

| Stakeholder | Value |
| --- | --- |
| Engineer onboarding to a new codebase | Ask "what does this file do?" / "what breaks if I change X?" instead of reading everything |
| Tech lead reviewing architecture | See layering, cycles, and complexity hot-spots at a glance |
| Open-source explorer | Understand an unfamiliar repo before contributing |
| The author (portfolio) | Demonstrates distributed-systems, AI/RAG, security, and full-stack skills |

## Scope

**In scope:** public repositories; import/file-level dependency analysis; the five
analyses above; RAG chat with sessions, citations, and file tagging; GitHub OAuth;
stars; public profiles; discovery hub.

**Out of scope (today):** private repositories requiring user tokens; symbol/call-level
("function A calls function B") graphs — the analyzer currently emits file-level
`import` edges only; multi-tenant billing; write operations back to GitHub.

## Non-goals

- Not a linter or CI gate — it is a *comprehension* tool.
- Not a code editor — it is read-only over a cloned snapshot.
- Not a real-time collaboration product — analysis is a point-in-time snapshot per commit.

## Key technical highlights

- **Clean separation**: the analysis engine is a standalone Python library with its own
  `pyproject.toml`, reusable outside the web app.
- **Async everywhere**: FastAPI + SQLAlchemy 2.0 async + asyncpg; SSE streaming for both
  analysis progress and chat tokens.
- **Resilient jobs**: a unique partial index prevents duplicate concurrent analyses, a
  heartbeat column + background **reaper** recovers from worker crashes.
- **Provider-agnostic AI**: LLM and embedding providers are selected purely by
  environment variables (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`) — no code changes to swap
  Ollama ↔ Groq or local ↔ HuggingFace.
- **Security-conscious**: GitHub URL validation (SSRF), path-traversal guards, IDOR
  checks on every owned resource, httpOnly JWT cookies, per-IP rate limiting.

See [architecture-summary.md](architecture-summary.md) for the technical overview and
[design-decisions.md](design-decisions.md) for the "why".
