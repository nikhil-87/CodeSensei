# Scalability & Performance Q&A

### "What are the scaling dimensions?"
Three independent ones: **request throughput** (API), **analysis throughput** (workers), and
**retrieval/AI** (vector store + LLM). They scale separately because they're decoupled by the
queue and the per-repo vector collections.

### "How do you scale the API?"
The backend is stateless (state lives in Postgres/Redis/Chroma), so I add replicas behind a
reverse proxy / load balancer. The one caveat is the in-memory rate limiter — for multiple
replicas I'd move it to a Redis-backed sliding window so limits are global.

### "How do you scale analysis?"
Add worker processes/containers — RQ is multi-consumer safe. The unique active-job index
guarantees one analysis per repo even with many workers. CPU-bound parsing is also
parallelized within a job. For very large repos I'd add incremental (changed-files-only)
re-analysis.

### "How do you scale retrieval?"
Per-repo Chroma collections keep each working set small, so ANN stays fast regardless of total
corpus size. At larger scale I'd consolidate onto **pgvector** (one fewer service, joins with
relational data) or a managed vector DB (Qdrant/Pinecone) — abstracted behind
`ChromaVectorStore`, so it's a one-class change + re-index.

### "Database scaling?"
Connection pooling today (`POSTGRES_POOL_SIZE`/overflow). Next steps: read replicas for the
heavy read paths (graph, discover), and partitioning `dependencies`/`symbols` by repository if
a single repo's analysis grows huge. Hot queries are already indexed
(`metrics(cyclomatic)`, `symbols(is_used)`, the chat-session composite index, `star_count`).

### "LLM rate limits / cost?"
The free Groq tier caps ~30 req/min. Mitigations: provider is env-swappable (Ollama/local or a
paid tier), and I'd add request queueing/backpressure and response caching for repeated
questions. Embeddings are computed once at index time, not per query.

### "What's the slowest part and how do you keep UX good?"
Cloning + parsing + embedding a large repo. UX stays good because it's **async**: the API
returns `202` instantly and the UI streams progress via SSE with a staged progress bar.
Insight pages are cached (Redis + TanStack Query). The graph clusters folders so even a
1000-file repo renders without choking.

### "How would this look at 100x users?"
Stateless API replicas + autoscaling worker pool; managed Postgres with read replicas;
Redis-backed rate limiting + queue; pgvector or managed vector DB; a CDN for the SPA; object
storage for cloned snapshots; and per-tenant quotas. The current design already separates the
axes that would need to scale, so it's evolution, not a rewrite.

### "Caching strategy?"
Two layers: server-side Redis for analysis read-models (TTL `REDIS_CACHE_TTL_SECONDS`), and
client-side TanStack Query (1-min default staleness, 5-min for insights) with mutation-driven
invalidation. Embeddings are effectively a cache of "code → vector" rebuilt only on
re-analysis.
