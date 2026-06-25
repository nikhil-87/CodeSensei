# Docker — Compose stacks

```
docker/
├── docker-compose.yml                 # Base stack: frontend, backend, worker, postgres, redis, chroma, ollama
├── docker-compose.dev.yml             # Overrides: bind-mounts, hot reload, debug ports
├── docker-compose.prod.yml            # Overrides: read-only fs, healthchecks, restart policies
└── docker-compose.observability.yml   # Prometheus + Grafana stack (separate so devs can opt-out)
```

## Why three files?

| File                              | Purpose                                                       |
| --------------------------------- | ------------------------------------------------------------- |
| `docker-compose.yml`              | Production-shaped base. Used in CI image builds.              |
| `docker-compose.dev.yml`          | Adds source volume mounts so `make up-dev` enables hot reload |
| `docker-compose.prod.yml`         | Hardening overlays: `read_only`, `cap_drop: ALL`, `no-new-privileges` |
| `docker-compose.observability.yml` | Prometheus + Grafana; opt-in to save 800 MB RAM during dev    |

Compose v2 file-merging order (`-f base -f dev`) means later files win on
key collisions, never on lists — so volumes/env_files append.
