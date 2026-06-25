# Deployment Documentation

CodeSensei is designed for **low coupling**: environments and providers are selected by
environment variables, so moving between them is mostly a `.env` change.

| Doc | Covers |
| --- | --- |
| [local.md](local.md) | Run everything locally with Docker Compose, from zero |
| [codespaces.md](codespaces.md) | GitHub Codespaces setup, secrets, OAuth callbacks |
| [oracle-cloud.md](oracle-cloud.md) | Oracle Cloud Free Tier VM, from zero, with TLS |
| [environment-variables.md](environment-variables.md) | Every env var: purpose, example, required?, impact if missing |
| [providers.md](providers.md) | Swapping OAuth / LLM / embeddings / DB / Redis providers |
| [migration.md](migration.md) | Move between environments/providers with minimal change |

## The three supported environments

| Environment | LLM | Embeddings | Postgres | Redis | Compose file |
| --- | --- | --- | --- | --- | --- |
| Local (full) | Ollama (local) | Ollama/local | container | container | `docker/docker-compose.yml` (+ `.dev.yml`) |
| Local (free-tier shape) | Groq | HuggingFace/local | container or Neon | container or Upstash | `docker/docker-compose.free-tier.yml` |
| Oracle Cloud Free Tier | Groq | HuggingFace/local | Neon | Upstash | `docker/docker-compose.free-tier.yml` |

## Standard commands (free-tier compose)
From the repo root:
```bash
# Bring everything up (build images)
docker compose -f docker/docker-compose.free-tier.yml --env-file .env up -d --build

# Rebuild just the frontend
docker compose -f docker/docker-compose.free-tier.yml --env-file .env up -d --build frontend

# Apply DB migrations (backend does NOT auto-migrate)
docker exec codesensei-backend alembic upgrade head

# Health
docker ps --filter "name=codesensei" --format "{{.Names}} {{.Status}}"
```

## Why migration is cheap
- Backend/worker/frontend are **stateless**; all state is in Postgres/Redis/Chroma.
- Providers are env-selected (`LLM_PROVIDER`, `EMBEDDING_PROVIDER`, `POSTGRES_*`,
  `REDIS_*`, OAuth vars).
- The only env-specific values are URLs/keys (OAuth callback, frontend base URL, provider
  endpoints). See [migration.md](migration.md).
