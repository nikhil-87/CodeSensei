# GitHub Codespaces Deployment

Run CodeSensei in a browser-based dev environment with zero local setup.

## 1. Create a Codespace
From the GitHub repo: **Code → Codespaces → Create codespace on main**. Codespaces builds a
Linux container with Docker available.

## 2. Configure secrets
Add repository/Codespaces **secrets** (Settings → Secrets and variables → Codespaces) so
they're injected as env vars — never commit them:
- `APP_SECRET_KEY`
- `GROQ_API_KEY`, `HUGGINGFACE_API_KEY`
- `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET` (if using real OAuth)
- `POSTGRES_PASSWORD`, `REDIS_PASSWORD` (or external Neon/Upstash creds)

In the Codespace, create `.env` from `.env.example` and reference these.

## 3. OAuth callback URLs (the Codespaces gotcha)
Codespaces exposes ports on dynamic forwarded URLs like
`https://<name>-3000.app.github.dev`. Your GitHub OAuth app must list the **forwarded**
callback:
- Homepage URL: `https://<name>-3000.app.github.dev`
- Authorization callback URL:
  `https://<name>-8000.app.github.dev/api/v1/auth/github/callback`

Set `GITHUB_OAUTH_CALLBACK_URL` and `FRONTEND_BASE_URL` to the matching forwarded URLs in
`.env`. (For quick exploration, set `MOCK_AUTH=true` and skip OAuth entirely.)

## 4. Run
```bash
docker compose -f docker/docker-compose.free-tier.yml --env-file .env up -d --build
docker exec codesensei-backend alembic upgrade head
```
Make ports **3000** and **8000** public (Ports panel) so the forwarded URLs work in the
browser and for OAuth.

## 5. Persistent storage considerations
- Codespaces storage is **ephemeral** — a rebuilt/deleted Codespace loses container
  volumes (Postgres/Chroma data). For durable data use **external Neon (Postgres)** and
  **Upstash (Redis)**; Chroma can be re-built by re-analyzing repos.
- Treat Codespaces as a dev/demo environment, not production.

## Limitations
- Dynamic forwarded URLs change per Codespace → OAuth app must be updated or use mock auth.
- Free Codespaces hours are limited; stop the Codespace when idle.
- Lower CPU/RAM than a dedicated VM → large-repo analysis is slower.

## Troubleshooting
- **OAuth redirect mismatch** → the callback URL in the GitHub app must exactly match
  `GITHUB_OAUTH_CALLBACK_URL`.
- **Blank app / API errors after rebuild** → re-run migrations; re-check `.env`.
- General catalogue: [../troubleshooting/README.md](../troubleshooting/README.md).
