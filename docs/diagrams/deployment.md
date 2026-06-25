# Deployment Topology Diagrams

## Local (Docker Compose, free-tier shape)

```mermaid
flowchart TB
  dev([Developer browser]) -->|:3000| fe[frontend container]
  dev -->|:8000| be[backend container]
  fe --> be
  be --> pg[(postgres container :5432)]
  be --> rd[(redis container :6379)]
  be --> ch[(chroma container :8000)]
  be -->|cloud| groq[Groq]
  rd --> wk[worker container]
  wk --> pg
  wk --> ch
  wk -->|cloud| hf[HuggingFace]
```

## GitHub Codespaces

```mermaid
flowchart TB
  user([Browser]) -->|forwarded :3000| fe[frontend]
  user -->|forwarded :8000| be[backend]
  fe --> be
  be --> pg[(Neon Postgres - external)]
  be --> rd[(Upstash Redis - external)]
  be --> ch[(chroma container)]
  be --> groq[Groq]
  rd --> wk[worker]
  wk --> pg
  wk --> ch
  wk --> hf[HuggingFace]
  note["OAuth callback uses the dynamic *.app.github.dev URL (or MOCK_AUTH=true)"]
```

## Oracle Cloud Free Tier (production-shaped)

```mermaid
flowchart TB
  user([Internet]) -->|HTTPS 443| ng[nginx + Let's Encrypt<br/>on the VM]
  ng -->|/| fe[frontend container :3000]
  ng -->|/api| be[backend container :8000]
  fe --> be
  be --> pg[(Neon Postgres - managed)]
  be --> rd[(Upstash Redis - managed)]
  be --> ch[(chroma container + volume)]
  be --> groq[Groq]
  rd --> wk[worker container]
  wk --> pg
  wk --> ch
  wk --> hf[HuggingFace]
  subgraph VM[Oracle A1 VM - always free]
    ng
    fe
    be
    wk
    ch
  end
```

Notes:
- Compute (frontend/backend/worker) is stateless; durable state is Neon + Upstash + the
  Chroma volume.
- Both the OCI security list **and** the host iptables must allow 80/443.
- Migration between these topologies is mostly a `.env` change — see
  [../deployment/migration.md](../deployment/migration.md).
