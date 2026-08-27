# CodeSensei Engineering Vault — Master Knowledge Base & Interview Guide

> **System Name:** CodeSensei (GitHub Repository Intelligence Platform)  
> **Repository Root:** `c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform`  
> **Source of Truth:** Workspace codebase as verified on August 27, 2026.  
> **Status:** Production-ready proof-of-concept / portfolio platform operating on zero-cost free-tier infrastructure.

---

## 1. Executive Summary & Purpose

The **CodeSensei Engineering Vault** is a complete, codebase-grounded documentation suite. It was generated through systematic static analysis of the entire repository—tracing models, migrations, endpoints, services, background workers, parsing pipelines, RAG implementations, and frontend architecture.

This vault serves two distinct objectives:
1. **Definitive Technical Documentation:** An exhaustive, implementation-level manual enabling any software engineer or architect to understand exactly how the entire system functions, how data flows, and where every responsibility lives.
2. **Staff/Senior SWE & System-Design Interview Preparation:** A defensible guide for technical interviews, detailing architecture decisions, concurrency controls, trade-offs, security postures, failure modes, database schema design, and scaling paths.

---

## 2. The Golden Rule: Codebase is the Source of Truth

Every claim, diagram, metric, and schema in this vault is derived directly from the code. Where features or scaling tiers are not present in the current codebase, they are explicitly tagged:
- **`[IMPLEMENTED]`** — Verified directly in application code, active migrations, or configuration.
- **`[PARTIALLY IMPLEMENTED]`** — Framework exists in code but lacks full operationalization or automated testing.
- **`[PLANNED / PROPOSED]`** — Architectural evolution path designed to solve specific scaling bottlenecks, but not yet present in production code.
- **`[CANNOT BE VERIFIED]`** — External third-party infrastructure behavior or metrics that require live runtime telemetry.

---

## 3. Master Document Index

The documentation suite is partitioned into 25 dedicated markdown documents covering all 24 engineering dimensions:

| Document | File Path | Core Subject Matter |
| :--- | :--- | :--- |
| **00. Master Index** | [00-MASTER-INDEX.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/00-MASTER-INDEX.md) | Navigation hub, reading tracks by persona, ground-truth standards |
| **01. Project Overview** | [01-project-overview.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/01-project-overview.md) | Problem statement, high-level architecture diagram, core capabilities |
| **02. Functional Requirements** | [02-functional-requirements.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/02-functional-requirements.md) | Implemented vs planned user, system, AI, and processing capabilities |
| **03. Non-Functional Requirements** | [03-non-functional-requirements.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/03-non-functional-requirements.md) | Grounded NFR analysis (security, reliability, performance, limits) |
| **04. Domain Model & Entities** | [04-domain-model-and-entities.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/04-domain-model-and-entities.md) | All 10 ORM models, migrations 0001–0007, constraints, Mermaid ER diagram |
| **05. Complete API Documentation** | [05-api-documentation.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/05-api-documentation.md) | All REST & SSE endpoints, request/response models, auth, error framing |
| **06. Authentication & Authorization** | [06-authentication-and-authorization.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/06-authentication-and-authorization.md) | GitHub OAuth, stateless JWT cookies, router guards, IDOR audit |
| **07. Complete User Flows** | [07-user-flows.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/07-user-flows.md) | Step-by-step user journeys with sequence diagrams and state transitions |
| **08. Current System Architecture** | [08-current-system-architecture.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/08-current-system-architecture.md) | Detailed C4 container architecture, communications, protocols, runtime |
| **09. Execution & Data Flows** | [09-execution-and-data-flows.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/09-execution-and-data-flows.md) | End-to-end sync/async data paths, pipeline sequences, RAG streaming |
| **10. Technology Stack** | [10-technology-stack.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/10-technology-stack.md) | Complete technology inventory, evaluation criteria, trade-offs, alternatives |
| **11. Engineering Problems & Solutions** | [11-engineering-problems-and-solutions.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/11-engineering-problems-and-solutions.md) | 8 real engineering challenges solved in code (concurrency, crash recovery, etc.) |
| **12. Reliability & Failure Handling** | [12-reliability-and-failure-handling.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/12-reliability-and-failure-handling.md) | Failure matrix across DB, Redis, Worker, LLM, network, and disk partitions |
| **13. Security Architecture** | [13-security-architecture.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/13-security-architecture.md) | SSRF defense, path traversal, injection protection, rate limiting, audit |
| **14. Performance** | [14-performance.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/14-performance.md) | Query optimization, caching patterns, parallel parsing, latency factors |
| **15. Scaling Architecture** | [15-scaling-architecture.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/15-scaling-architecture.md) | 9 scaling dimensions, progressive models (Stage 0 to Stage 3) |
| **16. Scalability Bottleneck Analysis** | [16-scalability-bottlenecks.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/16-scalability-bottlenecks.md) | Component bottleneck table, ranked bottlenecks, mitigation roadmap |
| **17. Testing Architecture** | [17-testing-architecture.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/17-testing-architecture.md) | Test pyramid, unit/integration/contract/e2e tests, fixtures, mocks |
| **18. Deployment & Infrastructure** | [18-deployment-and-infrastructure.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/18-deployment-and-infrastructure.md) | Docker Compose stacks, environment profiles, CI/CD pipelines |
| **19. Observability** | [19-observability.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/19-observability.md) | Structlog context, Prometheus metrics, readiness probes, Grafana |
| **20. Production Readiness Review** | [20-production-readiness-review.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/20-production-readiness-review.md) | Comprehensive 12-category operational readiness scorecard |
| **21. Interview Preparation Guide** | [21-interview-preparation-guide.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/21-interview-preparation-guide.md) | Senior/Staff SWE interview toolkit: pitches, deep dives, system design, Q&A |
| **22. Resume Fact Sheet** | [22-resume-and-portfolio-fact-sheet.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/22-resume-and-portfolio-fact-sheet.md) | Verifiable technical bullet points categorized with exact code citations |
| **23. "Do Not Claim" Section** | [23-do-not-claim.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/23-do-not-claim.md) | Anti-hallucination boundary: unverified, theoretical, or stubbed items |
| **24. Documentation Accuracy Audit** | [24-documentation-accuracy-audit.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/24-documentation-accuracy-audit.md) | Traceability verification matrix linking documentation directly to source code |
| **Master Technical Reference** | [PROJECT_SOURCE_OF_TRUTH.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/PROJECT_SOURCE_OF_TRUTH.md) | Authoritative single source of truth for the active codebase (for AI audits & interview prep) |

---

## 4. Reading Paths by Audience

### Track A: Software Engineering / System Design Interview Prep
For candidates preparing to pitch, explain, and defend this system in senior engineering interviews:
1. Start with [01-project-overview.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/01-project-overview.md) for the 30-second and 2-minute elevator pitch.
2. Read [11-engineering-problems-and-solutions.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/11-engineering-problems-and-solutions.md) to master the core technical challenges (concurrency races, worker crashes, dual-transaction streaming).
3. Review [15-scaling-architecture.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/15-scaling-architecture.md) and [16-scalability-bottlenecks.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/16-scalability-bottlenecks.md) for system design rounds (Stages 0 through 3).
4. Study [21-interview-preparation-guide.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/21-interview-preparation-guide.md) for direct question/answer defense.
5. Review [23-do-not-claim.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/23-do-not-claim.md) before drafting resume bullets or attending interviews.

### Track B: Backend & Distributed Systems Engineer
For engineers contributing to the FastAPI API, background workers, or persistence layer:
1. [04-domain-model-and-entities.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/04-domain-model-and-entities.md) — Schema, migrations, and relational constraints.
2. [05-api-documentation.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/05-api-documentation.md) — Complete endpoint reference.
3. [06-authentication-and-authorization.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/06-authentication-and-authorization.md) — Session management and access guards.
4. [09-execution-and-data-flows.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/09-execution-and-data-flows.md) — Background job lifecycle and transactional boundaries.
5. [12-reliability-and-failure-handling.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/12-reliability-and-failure-handling.md) — Failure recovery, timeouts, and stuck-job reaping.

### Track C: AI / Machine Learning Engineer
For engineers working on the RAG pipeline, embedding vectorization, or LLM integrations:
1. [08-current-system-architecture.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/08-current-system-architecture.md) (Section 5) — Vector store and provider topology.
2. [09-execution-and-data-flows.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/09-execution-and-data-flows.md) (Section 3) — End-to-end RAG retrieval and streaming token pipeline.
3. [11-engineering-problems-and-solutions.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/11-engineering-problems-and-solutions.md) (Problem 5 & 6) — Vector store tenant isolation and dual-transaction streaming.
4. [14-performance.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/14-performance.md) — Token latencies, embedding batch sizes, and context limits.

### Track D: Frontend Engineer
For engineers developing the React SPA, interactive graph, and real-time chat interface:
1. [07-user-flows.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/07-user-flows.md) — Complete user journeys and UI state transitions.
2. [05-api-documentation.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/05-api-documentation.md) — Contract definitions, SSE event shapes, and error structures.
3. [08-current-system-architecture.md](file:///c:/Users/nikhil/Desktop/projectss/github-repo-intelligence-platform/codesensei-github-repo-intelligence-platform/vault/08-current-system-architecture.md) (Section 1) — React 18, Vite, Cytoscape, and Zustand state topology.

---

## 5. Repository Ground-Truth Map

| Layer | Primary Location | Key Implementation Files |
| :--- | :--- | :--- |
| **Backend API** | `backend/app/` | `main.py`, `api/v1/router.py`, `core/dependencies.py`, `core/security.py`, `services/` |
| **Worker** | `worker/worker/app/` | `__main__.py`, `tasks/analyze_repository.py`, `persistence.py`, `progress.py` |
| **Analysis Engine** | `analysis-engine/engine/` | `orchestrator.py`, `parsers/registry.py`, `graph/builder.py`, `ai/rag_chain.py` |
| **Frontend SPA** | `frontend/src/` | `App.tsx`, `routes/router.tsx`, `pages/`, `components/`, `store/nodeContextStore.ts` |
| **Shared Specs** | `shared/config/` | `analysis_version.py`, `providers.py` |
| **Database Migrations** | `backend/alembic/versions/` | `0001_initial.py` through `0007_job_heartbeat.py` |
| **Deployments** | `docker/` | `docker-compose.yml`, `docker-compose.free-tier.yml`, `docker-compose.observability.yml` |
| **Pipelines** | `.github/workflows/` | `ci.yml`, `codeql.yml`, `release.yml` |
