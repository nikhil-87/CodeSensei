# Interview Preparation

A dedicated kit for defending this project in **Senior Software Engineer** / **System
Design** interviews. Everything here is grounded in the real implementation so answers hold
up to follow-ups.

| Doc | Use it for |
| --- | --- |
| [project-deep-dive.md](project-deep-dive.md) | The end-to-end walkthrough + elevator pitches |
| [hld-questions.md](hld-questions.md) | High-level design Q&A |
| [lld-questions.md](lld-questions.md) | Low-level / class / API / DB design Q&A |
| [security-questions.md](security-questions.md) | Security Q&A |
| [scalability.md](scalability.md) | Scaling & performance Q&A |
| [tradeoffs.md](tradeoffs.md) | Honest trade-offs & limitations |
| [behavioral.md](behavioral.md) | STAR stories rooted in this project |

## The 60-second pitch
> "CodeSensei is a GitHub repository intelligence platform — a small distributed system that
> clones any public repo, runs a multi-language static-analysis pipeline in a background
> worker, stores structured results in Postgres, indexes the code into a vector database,
> and lets you *ask questions* about the codebase that an LLM answers with citations via
> RAG. It's FastAPI + an RQ worker + a standalone analysis engine + React, with Postgres,
> Redis, and ChromaDB — designed to run entirely on free tiers, with production concerns
> handled: idempotent jobs, crash recovery via a heartbeat reaper, IDOR/SSRF defenses, SSE
> streaming, and observability."

## How to drive an interview with it
1. Start with the pitch, then draw the [system diagram](../diagrams/system-architecture.md).
2. Walk the **write path** (analysis) and the **read path** (RAG chat) — these show queues,
   workers, vector DB, and streaming.
3. Volunteer the **hard parts you solved**: duplicate-job prevention, worker-crash recovery,
   provider portability, the graph zoom/overlay bugs.
4. Be honest about **limitations** (file-level graph, free-tier rate limits) — it reads as
   senior, and you control the narrative.
