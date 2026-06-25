# Development & External Service Setup

This is the "I have an empty machine and accounts to create" guide for wiring up the
external services. For running the app see [../deployment/local.md](../deployment/local.md).

## GitHub OAuth app (real login)
1. GitHub → **Settings → Developer settings → OAuth Apps → New OAuth App**.
2. Fill in:
   - **Application name**: CodeSensei (dev)
   - **Homepage URL**: `http://localhost:3000` (or your domain / Codespaces URL)
   - **Authorization callback URL**:
     `http://localhost:8000/api/v1/auth/github/callback`
     (Codespaces: `https://<name>-8000.app.github.dev/...`; prod: `https://your-domain/...`)
3. Copy the **Client ID** and generate a **Client Secret**.
4. In `.env`: `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`,
   `GITHUB_OAUTH_CALLBACK_URL`, `FRONTEND_BASE_URL`.
5. **Common errors:** "redirect_uri mismatch" → callback URL must match exactly (scheme,
   host, port, path). For quick dev, set `MOCK_AUTH=true` and skip all of this.

## Groq (LLM)
1. Sign up at **console.groq.com** (no credit card).
2. Create an **API key** → `GROQ_API_KEY=gsk_...`.
3. `.env`: `LLM_PROVIDER=groq`, `GROQ_CHAT_MODEL=llama-3.3-70b-versatile`.
4. Free-tier limit ≈ 30 req/min. If chat 400s with a model error, the model was likely
   deprecated — update `GROQ_CHAT_MODEL`.

## HuggingFace (embeddings)
1. Sign up at **huggingface.co**.
2. **Settings → Access Tokens → New token** (read) → `HUGGINGFACE_API_KEY=hf_...`.
3. `.env`: `EMBEDDING_PROVIDER=huggingface`,
   `HUGGINGFACE_EMBED_MODEL=sentence-transformers/all-MiniLM-L6-v2`.
4. Alternative with no account: `EMBEDDING_PROVIDER=local` (CPU sentence-transformers).

## Ollama (fully local LLM + embeddings, optional)
1. Install from **ollama.com**; `ollama pull deepseek-coder:6.7b` and
   `ollama pull nomic-embed-text`.
2. `.env`: `LLM_PROVIDER=ollama`, `EMBEDDING_PROVIDER=ollama`, `OLLAMA_BASE_URL`.
3. Needs RAM/GPU; used by the full (non-free-tier) compose.

## PostgreSQL
- **Local container** (default dev): provided by compose; set `POSTGRES_*`.
- **Neon** (free serverless, recommended for cloud): create a project → copy the connection
  details → set `POSTGRES_HOST`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`,
  `POSTGRES_SSLMODE=require`.
- Then `docker exec codesensei-backend alembic upgrade head`.

## Redis
- **Local container** (default dev): set `REDIS_*`.
- **Upstash** (free serverless): create a database → copy host/password → set `REDIS_HOST`,
  `REDIS_PASSWORD`, `REDIS_TLS=true`. (The client keepalive is tuned for Upstash; keep the
  worker poll interval < 15s.)

## ChromaDB
- Runs as a container in compose; persistent volume `chroma-data`. Keep it on **port 8000**
  (the image ignores other port settings). Backup = back up the volume; rebuild =
  re-analyze repos.

## First-time verification checklist
- [ ] OAuth login works (or `MOCK_AUTH=true`)
- [ ] `alembic current` → `0007`
- [ ] Redis reachable (`/readyz` is 200)
- [ ] Submitting a repo → job runs to `succeeded`
- [ ] Insight pages render
- [ ] AI chat streams an answer **with citations**
- [ ] Worker logs show index step (or a logged `IndexingDegraded` if embeddings are off)

See [../deployment/environment-variables.md](../deployment/environment-variables.md) for
the full variable reference and [../deployment/providers.md](../deployment/providers.md) to
switch any provider.
