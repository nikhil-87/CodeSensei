# Architecture Documentation

Start here for how CodeSensei is designed.

| Doc | What it covers |
| --- | --- |
| [high-level-design.md](high-level-design.md) | Services, responsibilities, data flows, lifecycles, scaling, failure handling (C4 L2). |
| [low-level-design.md](low-level-design.md) | Backend layering contract, DI, key classes, API/streaming contracts, transactions. |
| [component-architecture.md](component-architecture.md) | Static/build-time view: monorepo layout + component dependency graph. |
| [analysis-pipeline.md](analysis-pipeline.md) | The clone→parse→graph→metrics→dead-code→architecture→persist→index pipeline. |

Related: [../database/schema.md](../database/schema.md) (data model),
[../ai/rag-pipeline.md](../ai/rag-pipeline.md) (RAG), [../decisions/](../decisions/) (ADRs),
[../diagrams/](../diagrams/) (all diagrams in one place).
