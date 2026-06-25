# Key Design Decisions (overview)

This is the *summary* of the most important decisions. Each has a full Architecture
Decision Record with context, options considered, and consequences in
[decisions/](../decisions/).

| Decision | Choice | One-line rationale | ADR |
| --- | --- | --- | --- |
| API framework | **FastAPI** (async) | Native async + Pydantic validation + OpenAPI for free; ideal for SSE streaming | [ADR-0001](../decisions/0001-fastapi.md) |
| Primary DB | **PostgreSQL** | Relational analysis data (files↔symbols↔deps), JSONB for citations, partial unique indexes | [ADR-0002](../decisions/0002-postgresql.md) |
| Queue / cache | **Redis + RQ** | Simple, free-tier-friendly background jobs; doubles as cache | [ADR-0003](../decisions/0003-redis-rq.md) |
| Vector store | **ChromaDB** | Self-hostable, free, simple upsert/query API, per-repo collections | [ADR-0004](../decisions/0004-chromadb.md) |
| Auth | **GitHub OAuth + JWT cookie** | Audience already has GitHub; httpOnly cookie avoids token-in-JS XSS risk | [ADR-0005](../decisions/0005-github-oauth.md) |
| AI approach | **RAG (not fine-tuning)** | Grounded answers with citations; works per-repo with zero training | [ADR-0006](../decisions/0006-rag.md) |
| Analysis engine | **Standalone library** | Decoupled, testable, reusable; AST + tree-sitter + regex fallback | [ADR-0007](../decisions/0007-analysis-engine.md) |
| Dependency graph | **File-level import edges** | Robust across languages; symbol/call edges deferred (honest limitation) | [ADR-0008](../decisions/0008-dependency-graph.md) |
| Provider strategy | **Env-driven, low coupling** | Swap LLM/embeddings/DB/Redis/OAuth by config, not code | [ADR-0009](../decisions/0009-provider-strategy.md) |
| Job safety | **Unique active-job index + heartbeat reaper** | Prevent duplicate analyses; recover from worker crashes | [ADR-0010](../decisions/0010-job-safety.md) |

## The themes behind the decisions

1. **Run on $0.** Every external dependency has a free tier and a self-hosted fallback.
   This drove Groq/HuggingFace/Neon/Upstash and the free-tier compose file.

2. **Production shape over feature count.** The system is intentionally a *complete*
   distributed system (queue, worker, vector store, migrations, observability, security)
   rather than a larger pile of features — because the goal is to demonstrate engineering
   maturity.

3. **Low coupling for portability.** Configuration, not code, selects environments and
   providers. This is what makes "migrate Codespaces → Oracle Cloud" a `.env` change.
   See [deployment/providers.md](../deployment/providers.md) and
   [deployment/migration.md](../deployment/migration.md).

4. **Honesty about limitations.** The dependency graph is file/import-level (no
   per-function call edges); the LLM/embeddings are free-tier (rate-limited); analysis is
   a point-in-time snapshot. These are documented, not hidden — see
   [interview/tradeoffs.md](../interview/tradeoffs.md).
