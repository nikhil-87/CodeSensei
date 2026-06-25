# System Architecture Diagrams

## Container view (C4 level 2)

```mermaid
flowchart TB
  user([User / Browser])
  subgraph Edge
    fe[Frontend SPA<br/>React + Vite + nginx]
  end
  subgraph Application
    be[Backend API<br/>FastAPI / uvicorn]
    wk[Worker<br/>RQ consumer]
  end
  subgraph Stateful
    pg[(PostgreSQL<br/>system of record)]
    rd[(Redis<br/>queue + cache)]
    ch[(ChromaDB<br/>vector store)]
  end
  subgraph External
    groq[Groq LLM]
    hf[HuggingFace embeddings]
    gh[GitHub OAuth + clone]
  end

  user -->|HTTPS| fe
  fe -->|/api/v1 JSON + SSE| be
  be -->|OAuth| gh
  be --> pg
  be --> rd
  be --> ch
  be -->|chat tokens| groq
  rd -->|jobs| wk
  wk -->|git clone| gh
  wk --> pg
  wk --> ch
  wk -->|embed| hf
```

## Component dependencies (build-time)

```mermaid
flowchart TD
  shared[[shared/config]]
  engine[[analysis-engine]]
  backend[backend]
  worker[worker]
  frontend[frontend]

  backend --> shared
  worker --> shared
  worker --> engine
  backend -. RAG building blocks .-> engine
  engine --> shared
  frontend -. HTTP only .-> backend
```

## Backend layering

```mermaid
flowchart LR
  R[Router - FastAPI] --> S[Service - business logic]
  S --> Repo[Repository - data access]
  Repo --> M[ORM Model]
  M --> PG[(PostgreSQL)]
  DI[DI container<br/>core/dependencies.py] -.builds.-> R
  DI -.builds.-> S
  DI -.builds.-> Repo
```
