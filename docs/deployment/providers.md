# Alternative Service Providers & Switching

CodeSensei is designed so that **any external dependency can be replaced by configuration**,
not code. This is the property that makes migration cheap.

## OAuth / Identity
| Provider | Config | Code change | Complexity |
| --- | --- | --- | --- |
| GitHub OAuth (default) | `GITHUB_OAUTH_*`, callback URL | none | — |
| Google / GitLab OAuth | new client in `AuthService` + provider value | ~1 service method | Low–Med |
| Auth0 / Clerk | swap `AuthService` to validate their tokens | moderate | Med |

The cookie/JWT session layer is provider-agnostic — only the "exchange code → profile" step
is provider-specific.

## LLM (chat)
| Provider | Config | Code change | Notes |
| --- | --- | --- | --- |
| Groq (default cloud) | `LLM_PROVIDER=groq`, `GROQ_API_KEY`, `GROQ_CHAT_MODEL` | none | OpenAI-compatible |
| Ollama (local) | `LLM_PROVIDER=ollama`, `OLLAMA_*` | none | needs RAM/GPU |
| OpenAI / Anthropic | add a client in `engine/ai/` + provider value | ~1 file | OpenAI is nearly drop-in |

## Embeddings
| Provider | Config | Re-index? | Notes |
| --- | --- | --- | --- |
| HuggingFace (default cloud) | `EMBEDDING_PROVIDER=huggingface`, `HUGGINGFACE_API_KEY` | — | 384-dim MiniLM |
| local sentence-transformers | `EMBEDDING_PROVIDER=local`, `LOCAL_EMBED_MODEL` | **yes** | no network |
| Ollama | `EMBEDDING_PROVIDER=ollama`, `OLLAMA_EMBED_MODEL` | **yes** | local |
| OpenAI / Cohere | add client + value | **yes** | different dims/space |

> Changing embedding provider/model changes the vector space → **re-analyze** affected
> repos so query-time and index-time models match. The `embedding_model` stamp records what
> was used.

## Database (Postgres)
| Provider | Config | Code change | Notes |
| --- | --- | --- | --- |
| Local container (default dev) | `POSTGRES_*` | none | — |
| Neon (free serverless) | `POSTGRES_HOST=<neon>`, `POSTGRES_SSLMODE=require` | none | recommended for cloud |
| Supabase / Railway | `POSTGRES_*` + SSL | none | any Postgres works |
Migration = dump/restore + point `POSTGRES_*` at the new host + run `alembic upgrade head`.

## Redis (queue + cache)
| Provider | Config | Code change | Notes |
| --- | --- | --- | --- |
| Local container (default dev) | `REDIS_*` | none | — |
| Upstash (free serverless) | `REDIS_HOST`, `REDIS_TLS=true`, `REDIS_PASSWORD` | none | TLS required; keepalive tuned |
| Redis Cloud / self-hosted | `REDIS_*` | none | — |
Redis holds only transient state (queue + cache); switching needs no data migration.

## Vector store
| Provider | Config | Code change | Notes |
| --- | --- | --- | --- |
| ChromaDB (default) | `CHROMA_*` | none | per-repo collections |
| pgvector / Qdrant / Pinecone | new store class implementing upsert/query | ~1 file + re-index | larger scale |

## The pattern
Each external dependency sits behind a small interface (`AuthService`, `engine/ai/*`
clients, repositories over SQLAlchemy, `RedisCache`, `ChromaVectorStore`). Selection is an
env value; adding a brand-new provider is typically **one new file + one enum value**. See
[../decisions/0009-provider-strategy.md](../decisions/0009-provider-strategy.md).
