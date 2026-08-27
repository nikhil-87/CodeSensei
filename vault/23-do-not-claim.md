# 23. "Do Not Claim" Section — Anti-Hallucination Boundaries

> **Purpose:** Explicit inventory of features, architectures, and performance metrics that are **NOT implemented** or only **partially implemented** in the repository.  
> **Rule:** In a senior engineering interview, claiming any of the items below as currently implemented will expose you if the interviewer inspects the codebase or asks probing technical follow-ups.

---

## 1. Top 8 Exaggeration Traps & Codebase Truths

### Trap 1: "We extract semantic AST symbols for 9 languages using Tree-sitter"
- **Temptation to Claim:** Stating that Tree-sitter is used to parse deep abstract syntax trees and extract functions, classes, and types for TypeScript, Go, Rust, Java, C++, etc.
- **The Codebase Truth:** In `analysis-engine/engine/parsers/tree_sitter_parser.py`:
  - Tree-sitter is used **only** to compute accurate lines of code (`lines_of_code`) and count branching control-flow nodes (`if`, `for`, `while`, `switch`) for cyclomatic complexity.
  - Tree-sitter **explicitly delegates symbol and import extraction to `RegexParser`**:
    ```python
    # In tree_sitter_parser.py:
    fallback = self._regex_fallback.parse(payload)
    # Merges LOC and branch count from Tree-sitter with symbols and imports from Regex!
    ```
  - Only **Python** has native, deep AST symbol and import extraction via Python's built-in `ast` standard library module.
- **Why You Will Get Caught:** An interviewer asking: *"How did you map Tree-sitter's concrete syntax tree node types across Go, Rust, and TypeScript grammars to a unified Symbol schema?"* will immediately reveal that Tree-sitter doesn't extract symbols in your code.
- **What to Say Instead:**
  > *"We implemented a pragmatic 3-tier parsing registry: for Python, we run full semantic AST extraction via Python's `ast` module. For other languages, we leverage Tree-sitter's concrete syntax tree to calculate robust LOC and cyclomatic branch counts without being tripped by comments or string literals, and delegate declaration extraction to tuned regex patterns."*

---

### Trap 2: "We built a symbol-level call graph (Function A calls Function B)"
- **Temptation to Claim:** Stating that the dependency graph shows which specific functions call other functions across the codebase.
- **The Codebase Truth:** In `analysis-engine/engine/graph/builder.py`, the dependency graph records **file-level import edges**, not function-level call edges:
  ```python
  # Edge connects from_file -> to_file based on import statements
  ```
  While `Symbol` rows are stored in the database, the `Dependency` table edges represent imports between files.
- **Why You Will Get Caught:** The interviewer will ask: *"How did you resolve dynamic function dispatches, polymorphic method calls, and imports aliased across files without running a compiler type-checker?"* You cannot defend call-graph resolution without a Language Server Protocol (LSP) indexer.
- **What to Say Instead:**
  > *"Our dependency graph operates at the file and module import level. It resolves import declarations to construct a directed graph between files, enabling cycle detection via Tarjan's SCC and file-level blast-radius impact analysis."*

---

### Trap 3: "We support private repositories using user GitHub tokens"
- **Temptation to Claim:** Stating that users can analyze their private company repositories securely.
- **The Codebase Truth:** The platform **only supports public repositories**:
  - The OAuth flow does not request the `repo` scope (only `read:user` and `user:email`).
  - User OAuth access tokens are **not stored** in the database.
  - `GitCloner` clones strictly via unauthenticated HTTPS (`git clone https://github.com/owner/repo.git`) with `GIT_TERMINAL_PROMPT=0` to reject password prompts.
- **Why You Will Get Caught:** The interviewer will ask: *"Where and how do you store user OAuth access tokens at rest, and how do you prevent worker processes from leaking those credentials in logs?"*
- **What to Say Instead:**
  > *"The current platform is designed for public repositories and avoids storing third-party OAuth access tokens entirely. Supporting private repositories is our primary Stage 1 architectural roadmap item, requiring AES-GCM token encryption at rest and ephemeral token injection into the clone sandbox."*

---

### Trap 4: "We use distributed Redis-backed rate limiting"
- **Temptation to Claim:** Stating that API endpoints are protected by a distributed Redis rate limiter.
- **The Codebase Truth:** In `backend/app/core/middleware.py`, `RateLimitMiddleware` maintains an **in-memory sliding window dictionary** inside the Python process:
  ```python
  self._requests: dict[str, list[float]] = {}
  ```
  If you spin up multiple API pods, each pod maintains its own independent rate-limit memory.
- **Why You Will Get Caught:** The interviewer will ask: *"How do you synchronize rate limit state across multiple load-balanced API containers?"*
- **What to Say Instead:**
  > *"Our current rate limiter is an in-memory sliding-window middleware suitable for a single container. As we document in our Stage 1 scaling plan, scaling horizontally across an ALB requires moving this state to a Redis token-bucket Lua script."*

---

### Trap 5: "We implemented an event-driven microservices architecture with Kafka"
- **Temptation to Claim:** Claiming the platform is built on microservices communicating asynchronously over Apache Kafka or RabbitMQ.
- **The Codebase Truth:** CodeSensei is a **clean, modular monolith with a background worker**:
  - Backend API (FastAPI) and Background Worker (RQ) share the same PostgreSQL database and Redis instance.
  - Communication is through simple Redis Queue (RQ) job specifications (`rq:queue:codesensei_analysis`).
- **Why You Will Get Caught:** The interviewer will ask about Kafka topic partitioning, consumer group rebalancing, and transactional outbox patterns, none of which exist in the codebase.
- **What to Say Instead:**
  > *"We deliberately chose a modular monolith with an asynchronous background worker using Redis Queue. This avoided distributed systems overhead and let us run the entire platform on zero-cost free-tier infrastructure while maintaining clean module boundaries."*

---

### Trap 6: "We perform incremental re-analysis using GitHub webhooks"
- **Temptation to Claim:** Stating that when a repo pushes new code, the system parses only the git diff.
- **The Codebase Truth:** The platform does not implement GitHub webhooks:
  - All re-analysis is triggered manually via `POST /api/v1/repositories/{id}/analyze`.
  - The worker performs a full shallow clone, wipes all prior file rows for that repo in PostgreSQL, and re-parses the entire repository from scratch.
- **Why You Will Get Caught:** The interviewer will ask: *"How do you patch Tarjan's SCC cycle groups incrementally when only one edge in the graph changes?"*
- **What to Say Instead:**
  > *"Currently, re-analysis executes a full clean wipe-and-replace pipeline. Incremental analysis via GitHub webhooks and git diff parsing is documented as our Stage 3 architectural evolution."*

---

### Trap 7: "Our system scales to millions of repositories with sub-5ms latencies"
- **Temptation to Claim:** Quoting massive enterprise performance numbers as current capabilities.
- **The Codebase Truth:** The platform is configured for free-tier constraints (512MB RAM backend, 1GB worker, 5-connection DB pool). It is designed to handle hundreds of repositories cleanly, not millions, without adopting the progressive scaling architectures (Stages 1–3).
- **What to Say Instead:**
  > *"On our current free-tier proof-of-concept deployment, cached graph reads return in 10–25ms, but worker throughput is limited to 1–2 concurrent analyses. We have documented a 4-stage progressive scaling model showing exactly how the architecture evolves to handle 10,000 to 10M repositories."*

---

### Trap 8: "We built custom fine-tuned LLM models for code analysis"
- **Temptation to Claim:** Claiming you trained or fine-tuned custom AI models.
- **The Codebase Truth:** The system uses **off-the-shelf foundation models via RAG**:
  - LLM: `llama-3.3-70b-versatile` served by Groq Cloud API, or `llama3.2:3b` via Ollama.
  - Embeddings: `sentence-transformers/all-MiniLM-L6-v2` via HuggingFace Inference API.
  - The engineering achievement is in **symbol-aware chunking, dual-transaction streaming, and context retrieval**, not model training.
- **What to Say Instead:**
  > *"We didn't train models; we engineered a robust RAG pipeline that grounds off-the-shelf foundation models in verified code chunks with symbol-aware boundaries, dual-transaction streaming isolation, and inline line-number citations."*

---

## 2. Summary Table of Claim Boundaries

| Area | DO NOT Claim ❌ | DO Claim Instead ✅ |
| :--- | :--- | :--- |
| **Parsing** | "Custom AST parsers for 9 languages" | "3-tier resilient registry: Python native AST, Tree-sitter for LOC/branching metrics, Regex fallback for declarations" |
| **Graph** | "Function-level call graph" | "File-level import dependency graph with cycle detection via Tarjan's SCC" |
| **Private Repos**| "Secure private repo analysis with GitHub OAuth" | "Public repository analysis; zero credential storage; private repos documented in Stage 1 roadmap" |
| **Architecture** | "Event-driven microservices on Kafka" | "Modular monolith + background worker using Redis Queue and burst-mode polling" |
| **Rate Limiting**| "Distributed Redis rate limiter" | "In-memory sliding-window middleware; Redis token-bucket planned for multi-replica scaling" |
| **AI / ML** | "Fine-tuned custom code intelligence LLM" | "Symbol-aware RAG pipeline with dual-transaction streaming and citation generation" |
| **Re-Analysis** | "Incremental Git diff re-parsing via webhooks"| "Atomic wipe-and-replace batch persistence; manual re-analysis trigger" |
