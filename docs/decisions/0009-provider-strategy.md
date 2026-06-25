# ADR-0009: Env-driven, low-coupling provider strategy

**Status:** Accepted

## Context
The app must run locally (Ollama, container Postgres/Redis) and on free tiers (Groq,
HuggingFace, Neon, Upstash) with **minimal change**, and must be migratable between
environments without code edits.

## Decision
Select every external provider via **environment variables** behind small interfaces:
- LLM: `LLM_PROVIDER` (`ollama`/`groq`)
- Embeddings: `EMBEDDING_PROVIDER` (`ollama`/`huggingface`/`local`)
- DB/Redis/Chroma: `POSTGRES_*`, `REDIS_*`, `CHROMA_*`
- OAuth: `GITHUB_OAUTH_*`

Clients live in `analysis-engine/engine/ai/`; data access is behind repositories; defaults
are centralized in `shared/config/defaults.py`. Adding a provider is typically one new file
+ one enum value.

## Alternatives considered
- **Hard-coded providers** — simplest, but couples the app to one vendor and blocks free-tier
  portability.
- **A plugin framework** — over-engineered for the number of providers.

## Consequences
- (+) Migration is a `.env` change (see [../deployment/migration.md](../deployment/migration.md)).
- (+) No vendor lock-in; same code runs in every environment.
- (+) Testable: providers can be stubbed by config.
- (−) More config surface (~60 env vars) → mitigated by a documented reference and sane
  defaults.
- (−) Embedding-provider changes require re-indexing (vector space differs) — flagged via
  the `embedding_model` stamp.
