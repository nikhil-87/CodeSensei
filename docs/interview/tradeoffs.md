# Trade-offs & Honest Limitations

Owning the trade-offs is what makes the project read as *senior*. Each item is a deliberate
choice with a reason and a known cost.

## Deliberate trade-offs

| Choice | Why | Cost / limitation |
| --- | --- | --- |
| **File/import-level dependency graph** | Robust + accurate across 9+ languages | Not a true per-function call graph; "usage" is file-level ([ADR-0008](../decisions/0008-dependency-graph.md)) |
| **RAG over fine-tuning** | Works on any repo instantly, grounded + cited | Quality bounded by retrieval + free embedding model ([ADR-0006](../decisions/0006-rag.md)) |
| **Free-tier LLM (Groq) + embeddings (MiniLM)** | $0, good enough | ~30 req/min cap; 384-dim embeddings limit semantic depth |
| **ChromaDB single-node** | Free, simple, per-repo isolation | Not sharded; would move to pgvector/managed at scale ([ADR-0004](../decisions/0004-chromadb.md)) |
| **In-memory per-IP rate limiter** | Zero extra infra | Per-replica behind a load balancer → move to Redis for prod |
| **Point-in-time analysis snapshot** | Simple, deterministic per commit | Goes stale on new commits; freshness banner + manual re-analyze (no auto webhook yet) |
| **JWT in cookie (stateless)** | No session store; replica-friendly | Pre-expiry revocation is awkward (mitigated by modest TTL) |
| **Best-effort indexing** | Structural analysis shouldn't fail on a flaky embedding API | Chat can be degraded until a successful re-index |
| **Monorepo** | One PR spans full features; shared config | Larger repo; needs change-filtered CI (which it has) |

## Known limitations (stated plainly)
- **No symbol/call edges** — the headline graph limitation; schema + UI are ready for them.
- **No retrieval re-ranking** — pure cosine ANN + guaranteed slots for tagged files.
- **Prompt injection** is mitigated, not eliminated (inherent to LLMs over untrusted code).
- **Rate limiting** isn't globally correct across replicas yet.
- **Analysis is not incremental** — a re-analysis re-parses the whole repo.
- **Private repos** aren't supported (no stored user tokens).

## What I'd do first with more time
1. Symbol/call-level graph + a function-level inspector.
2. Move rate limiting to Redis (multi-replica correctness).
3. Incremental re-analysis (changed files only) + webhook triggers.
4. Retrieval re-ranking + response caching for chat.
5. pgvector consolidation to drop a service at scale.

## How to present this in an interview
State the limitation, then immediately give the reason and the upgrade path. e.g.: *"The
graph is import-level, not call-level — accurate cross-language call resolution is brittle, so
I chose correctness over ambition. The schema already supports richer edges, so it's an
incremental analyzer upgrade, not a redesign."* That sequencing signals judgment, not gaps.
