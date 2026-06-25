# CodeSensei — Documentation Suite

> **➡️ The full topic map lives in [INDEX.md](INDEX.md).** Documentation is organized by
> topic (`overview/`, `architecture/`, `backend/`, `frontend/`, `database/`, `ai/`,
> `features/`, `security/`, `testing/`, `deployment/`, `development/`, `operations/`,
> `troubleshooting/`, `decisions/`, `interview/`, `reviews/`, `diagrams/`). For a single
> end-to-end handover document, read
> [MASTER_PROJECT_DOCUMENTATION.md](MASTER_PROJECT_DOCUMENTATION.md).

> **CodeSensei** is a GitHub Repository Intelligence Platform. Point it at a public
> GitHub repository and it clones, parses (tree-sitter), builds dependency/complexity/
> dead-code/impact analyses, and answers natural-language questions about the code
> using a Retrieval-Augmented Generation (RAG) pipeline over local or cloud LLMs.

This folder is the **single source of truth** for the system's design, operations,
security, and review material. It is organized by topic so each audience can go
straight to what it needs.

---

## How to read these docs

| If you are a… | Start here |
| --- | --- |
| Hiring manager / interviewer | [overview/executive-summary.md](overview/executive-summary.md) → [interview/defense-guide.md](interview/defense-guide.md) |
| Architect | [architecture/high-level-design.md](architecture/high-level-design.md) → [decisions/README.md](decisions/README.md) |
| Backend engineer | [architecture/low-level-design.md](architecture/low-level-design.md) → [development/code-walkthrough.md](development/code-walkthrough.md) |
| AI/ML engineer | [ai/rag-pipeline.md](ai/rag-pipeline.md) → [architecture/analysis-pipeline.md](architecture/analysis-pipeline.md) |
| DevOps / SRE | [deployment/README.md](deployment/README.md) → [operations/runbooks.md](operations/runbooks.md) |
| Security reviewer | [security/threat-model.md](security/threat-model.md) → [operations/production-readiness-review.md](operations/production-readiness-review.md) |
| New joiner (onboarding) | [MASTER_PROJECT_DOCUMENTATION.md](MASTER_PROJECT_DOCUMENTATION.md) → [development/code-walkthrough.md](development/code-walkthrough.md) |
| Skeptical staff engineer | [reviews/staff-engineer-review.md](reviews/staff-engineer-review.md) |

---

## Key documents

- **Overview** — [overview/executive-summary.md](overview/executive-summary.md), [overview/future-roadmap.md](overview/future-roadmap.md), [overview/risks-and-limitations.md](overview/risks-and-limitations.md), [overview/changelog.md](overview/changelog.md)
- **Architecture** — [architecture/high-level-design.md](architecture/high-level-design.md), [architecture/low-level-design.md](architecture/low-level-design.md), [architecture/analysis-pipeline.md](architecture/analysis-pipeline.md), [decisions/README.md](decisions/README.md)
- **AI / RAG** — [ai/rag-pipeline.md](ai/rag-pipeline.md), [ai/providers.md](ai/providers.md), [ai/vector-store.md](ai/vector-store.md)
- **Security** — [security/threat-model.md](security/threat-model.md)
- **Deployment & Ops** — [deployment/README.md](deployment/README.md), [deployment/migration.md](deployment/migration.md), [operations/runbooks.md](operations/runbooks.md), [operations/production-readiness-review.md](operations/production-readiness-review.md), [operations/performance.md](operations/performance.md)
- **Development** — [development/code-walkthrough.md](development/code-walkthrough.md), [testing/README.md](testing/README.md), [testing/verification/](testing/verification/)
- **Reviews & interview** — [reviews/staff-engineer-review.md](reviews/staff-engineer-review.md), [reviews/architecture-review.md](reviews/architecture-review.md), [interview/defense-guide.md](interview/defense-guide.md)

For the complete, audience-segmented index see [INDEX.md](INDEX.md).

---

## Documentation conventions

- **Mermaid** for all diagrams (renders natively on GitHub).
- **Tables** for comparisons, contracts, and config references.
- **Brutal honesty** — limitations and tech debt are documented, not hidden
  (see [reviews/staff-engineer-review.md](reviews/staff-engineer-review.md)).
- Facts are kept consistent with code; exact versions are in the root
  [README.md](../README.md) and [shared/config/defaults.py](../shared/config/defaults.py).
