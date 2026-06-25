# Architecture Decision Records (ADRs)

Each ADR captures one significant decision: its **context**, the **decision**, the
**alternatives** considered, and the **consequences** (good and bad). They are immutable
records — if a decision changes, add a new ADR that supersedes the old one.

| ADR | Decision |
| --- | --- |
| [0001](0001-fastapi.md) | FastAPI for the backend |
| [0002](0002-postgresql.md) | PostgreSQL as the system of record |
| [0003](0003-redis-rq.md) | Redis + RQ for background jobs |
| [0004](0004-chromadb.md) | ChromaDB as the vector store |
| [0005](0005-github-oauth.md) | GitHub OAuth + JWT cookie auth |
| [0006](0006-rag.md) | RAG (not fine-tuning) for AI |
| [0007](0007-analysis-engine.md) | Standalone analysis engine library |
| [0008](0008-dependency-graph.md) | File-level import dependency graph |
| [0009](0009-provider-strategy.md) | Env-driven, low-coupling provider strategy |
| [0010](0010-job-safety.md) | Unique active-job index + heartbeat reaper |
