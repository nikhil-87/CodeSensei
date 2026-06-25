# Troubleshooting Guide

A symptom → root cause → fix catalogue. Many of these were real bugs fixed during
development; the lessons are captured here so they don't recur.

## Analysis & jobs

| Symptom | Root cause | Fix |
| --- | --- | --- |
| Repo stuck in `ANALYZING` forever | Worker crashed mid-job | Reaper fails it after the heartbeat timeout; restart worker + re-analyze |
| "Analyze" returns `409` | An active job already exists (`uq_active_job_per_repository`) | Wait for it / check `…/jobs/latest`; this is correct behavior |
| Job `SUCCEEDED` but chat is generic | Indexing degraded (Chroma/embeddings unreachable) | Check worker logs for `IndexingDegraded`; fix provider; re-analyze |
| Analysis never starts | Worker not consuming (bad Redis creds) | Verify `REDIS_TLS`/password; check worker logs |

## AI / chat

| Symptom | Root cause | Fix |
| --- | --- | --- |
| Chat 400 / "model not found" | Groq model deprecated | Update `GROQ_CHAT_MODEL` (e.g. `llama-3.3-70b-versatile`) |
| Chat throttled / 429-ish | Groq free-tier ~30 req/min | Slow down / upgrade tier / switch provider |
| Answers ignore the repo | Repo not indexed, or embedding model changed | Re-analyze; ensure `EMBEDDING_PROVIDER` + key consistent |
| Streaming "Attempted to access streaming response content" | Reading a streamed body before `.read()` | (Fixed) read the response body before `.json()`/`.text` in the Groq client |

## Database

| Symptom | Root cause | Fix |
| --- | --- | --- |
| `/readyz` 503 | Postgres/Redis unreachable | Fix `POSTGRES_*` / `REDIS_*`; Neon needs `sslmode=require` |
| App errors after deploy | Migrations not applied | `docker exec codesensei-backend alembic upgrade head` (expect `0007`) |

## ChromaDB

| Symptom | Root cause | Fix |
| --- | --- | --- |
| Vector ops fail / wrong port | Image always binds 8000; client pointed elsewhere | Keep service **and** client on `CHROMA_PORT=8000` |
| Old embeddings linger after delete | — | Repo delete drops the collection automatically; if orphaned, delete `repo_<id>` |

## Frontend / UI

| Symptom | Root cause | Fix |
| --- | --- | --- |
| Dependency graph blank / faint "translucent" smear | cose-bilkent `animate:"end"` fit latched onto collapsed positions → zoom clamped to max, graph off-screen | (Fixed) `animate:false` + a settle-timeout `cy.fit()` after layout |
| Something wide covers the graph | Global `.cytoscape-host > div { width/height:100% }` also stretched the controls overlay | (Fixed) exclude overlays via `:not([data-graph-overlay])` + tag overlays |
| Repository card cut off on the right (mobile) | A *classic* (non-overlay) scrollbar painting over the card's padding | (Fixed) `scrollbar-gutter: stable` on `<main>` + `min-w-0`/truncation on the card |
| Horizontal scrollbar on mobile | Inline pagination row overflowing | (Fixed) responsive `Pagination` (numbered ≥sm, chevrons on mobile) |
| Chat composer pushed off-screen on mobile | `Card` wraps children in an unstyled div, breaking the flex-height chain | (Fixed) `Card` `contentClassName` + `min-h-0 flex-1` chain |
| Pages render narrow on desktop | Making the shared `<main>` a flex column broke `mx-auto max-w-*` stretch | (Lesson) keep `<main>` a block; never make it `flex flex-col` |
| Complexity chart unreadable on phone | Vertical bars + rotated labels cramped | (Fixed) horizontal bars under 639px via `useMediaQuery` |
| New code not showing | Browser served the cached hashed bundle | Hard-refresh (Ctrl+Shift+R); confirm the new `index-*.js` hash is served |

## Deployment

| Symptom | Root cause | Fix |
| --- | --- | --- |
| Oracle site unreachable | OCI security list OR host iptables blocking 80/443 | Open **both** layers |
| OAuth redirect mismatch | Callback URL ≠ GitHub app | Make them identical (scheme/host/port/path) |
| CORS blocked | `APP_CORS_ORIGINS` missing the frontend origin | Add it |

## Diagnostics cheatsheet
```bash
docker ps --filter "name=codesensei" --format "{{.Names}} {{.Status}}"
docker compose -f docker/docker-compose.free-tier.yml logs --tail=200 worker
docker exec codesensei-backend alembic current
curl -s http://localhost:8000/api/v1/readyz
```

## Testing/verification gotchas
- The embedded browser **cannot screenshot** Cytoscape's accelerated canvas (always blank).
  Verify the graph via the live `cy` instance: `cy.zoom()`, `node.renderedPosition()` within
  `cy.width()/height()`, `node.hasClass('dimmed')`.
- Headless Chromium uses 0-width overlay scrollbars → it won't reproduce classic-scrollbar
  clipping; force one in tests to reproduce.
- PowerShell mangles inline JSON for `curl` → write the body to a temp file.
