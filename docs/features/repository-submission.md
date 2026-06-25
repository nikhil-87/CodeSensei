# Feature: Repository Submission

## What it does
Accepts a GitHub repository URL (and optional branch), validates it, records it, and kicks
off a background analysis job.

## Why it exists
It's the entry point of the whole product — turning "a URL" into "an analyzable, queryable
repository". Validation here is also the system's main **SSRF** defense.

## User workflow
1. Click "Add repository" → dialog.
2. Paste a GitHub HTTPS URL, optionally a branch.
3. Submit:
   - **New repo** → `202` with a job → redirected to the dashboard, which streams progress.
   - **Already analyzed by you** → the dialog switches to a choice: **Refresh analysis** /
     **Open existing analysis** / **Cancel** (no duplicate is created).
   - **Already analyzing** → taken straight to the live progress.

## Backend implementation
- **Route:** `POST /repositories` (`repositories.py`).
- **Service:** `RepositoryService.submit(payload, owner_id)`:
  1. `validate_github_url(url)` (`core/security.py`) — canonical HTTPS only; rejects SSH,
     ports, userinfo, query strings, non-GitHub hosts.
  2. `validate_branch_name(branch)` — rejects `..`/path tricks.
  3. If the caller already has this `(url, branch)`: raise `RepositoryAlreadyExistsError`
     (`409 repository_already_exists`, with the existing `repository_id`) — or
     `AnalysisAlreadyRunningError` (`409 analysis_already_running`) if a job is in flight.
     **No duplicate row is created and no silent re-analysis happens.**
  4. Otherwise insert `repositories` (`PENDING`) + `analysis_jobs` (`QUEUED`) in one
     transaction.
  5. `JobDispatcher.enqueue_analysis(repo_id, job_id)`.
  6. Return `(Repository, AnalysisJob)`.
- The `uq_repositories_owner_id_url_branch` unique constraint backs the per-user
  one-row-per-`(url, branch)` guarantee.

## Frontend implementation
- `RepositoryAddDialog` collects URL + branch, validates shape client-side, calls
  `useCreateRepository()`. On `409 repository_already_exists` it shows a
  **Refresh / Open existing / Cancel** choice (Refresh calls `AnalysisApi.trigger`); on
  `409 analysis_already_running` it opens the dashboard.

## Tables involved
- `repositories` (insert/upsert), `analysis_jobs` (insert).

## APIs
`POST /repositories` → `202 AnalysisJobRead`, or `409 repository_already_exists` /
`409 analysis_already_running` (both carry the existing `repository_id` in `details`).

## Edge cases handled
- **Malicious/SSRF URL** — rejected before any network/clone.
- **Duplicate submit (same user)** — `409 repository_already_exists` → dialog offers
  Open/Refresh/Cancel; no duplicate row.
- **Already analyzing** — `409 analysis_already_running` → opens live progress.
- **Oversized repos** — guarded later by `API_MAX_REPO_SIZE_MB` / `API_MAX_REPO_FILES`.
- **Default branch** — `branch` null means "use the repo default".

## Security considerations
- URL validation is the SSRF boundary (no internal hosts, no scheme tricks).
- Ownership is taken from the authenticated cookie, never from the request body.
See [../security/threat-model.md](../security/threat-model.md).

## Future improvements
- Private repos (user-supplied, encrypted tokens).
- Webhook-driven re-analysis on push.
- Monorepo subpath selection.
