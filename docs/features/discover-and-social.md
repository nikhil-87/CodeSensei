# Feature: Discover, Stars & Profiles

Three social/discovery features that make analyzed repositories shareable.

## Public Repositories / Discover (repository-centric)
**What:** owners can mark a repo public; anyone can browse a discovery hub. The hub is
**repository-centric**: a `(url, branch)` repository may be analyzed and made public by
several users, but it appears as **one card**, not one per analysis. Opening a card shows
the repository overview with **all** its public analyses.
**Why:** the same repo analyzed by User A (Jan), B (Feb), C (Mar) are distinct analyses
(code changed, engine improved, AI insights differ) — Discover shouldn't duplicate the
listing nor collapse them into one. So: one repository entry, many selectable analyses.

**Flow:** Discover → Repository (overview) → Available public analyses → Selected analysis.

- **Visibility:** `PATCH /repositories/{id}/visibility` (owner) toggles `is_public`.
- **Discover (grouped):** `GET /discover/repositories` →
  `RepositoryService.list_public_grouped` collapses public, `READY` rows by `(url, branch)`
  via a window function; the most-recent analysis is the representative
  (`latest_repository_id`), with `analyses_count` and summed `total_stars`. Sortable
  (stars/recent/name), searchable, paginated.
- **Repository overview:** `GET /discover/repository?url=&branch=` →
  `RepositoryService.public_repository_group` returns `RepositoryGroupDetail` (header +
  every public analysis as `PublicAnalysisRead`, newest first, each with analyst, date,
  version stamps, star count, freshness). `url` is validated/canonicalized.
- **Frontend:** `DiscoverPage` → `DiscoverRepositoryCard` (one per repo);
  `RepositoryAnalysesPage` (route `/discover/r?u=<url>&b=<branch>`) renders the overview +
  an `Analysis #N` card per public analysis with an **Open analysis** button and a
  freshness pill (`Latest available` / `Refresh recommended`). Analyst names link to their
  public profile.

## Stars / Favorites
**What:** star/unstar any repo; a "Your stars" page lists them.
**Why:** bookmark useful repos; rank discovery by popularity.
- **APIs:** `PUT /repositories/{id}/star`, `DELETE /repositories/{id}/star`, `GET /me/stars`.
- **Service:** `StarService` — idempotent toggle, maintains denormalized
  `repositories.star_count`, returns the new count so the UI reconciles optimistic state
  (this fixed an earlier star-count race).
- **Table:** `stars` with `uq_stars_user_repository` (one star per user/repo).
- **Frontend:** `StarButton` (optimistic), `StarredPage`.

## User Profiles
**What:** a public profile page per username with avatar, stats, and their public repos.
Reached by clicking an **analyst name** on any public analysis, or `/u/{username}` directly.
**Why:** attribute analyses to people; a portfolio surface.
- **APIs:** `GET /users/{username}`, `GET /users/{username}/repositories`.
- **Service:** `ProfileService.get_profile` (public repo count + total stars),
  `list_public_repositories`.
- **Frontend:** `ProfilePage` (`useProfile` + `useProfileRepositories`).
- **Privacy:** only public-safe fields are exposed (no email); private repos, private
  analyses, and chat sessions are never surfaced. A deleted analyst shows as "Unknown" with
  no link.

## Edge cases handled
- **Same user re-submits a repo** → `409 repository_already_exists` → Open/Refresh/Cancel
  (no duplicate row). See [repository-submission.md](repository-submission.md).
- **Multiple users analyze the same repo** → each is a distinct `repositories` row; Discover
  groups them under one repository card, the overview lists each analysis.
- **Repo becomes private / made-private after being public** → it instantly drops out of
  Discover, the grouped query, and profiles (filters on `is_public` + `READY` at read time).
- **Repo deleted / analysis failed / still analyzing** → not `READY` → excluded from public
  surfaces.
- **Outdated analysis** → freshness pill (`Refresh recommended`) on the analysis + repo cards.
- **User account deleted** → `owner_user` is null → analyst shows as "Unknown", unlinked.
- **Multiple analyses on the same day** → separate rows, ordered by `analyzed_at` then
  `created_at`; each gets its own `Analysis #N` card.
- Double-star / double-unstar — idempotent.
- Unknown username → friendly 404 empty state.
- Pagination is fully responsive (numbered ≥sm, chevrons on mobile).

## Security considerations
- Only `is_public` + `READY` repos are exposed via discover/profiles/overview; everything
  else is `404`. The grouped query and the overview both filter on these at read time, so a
  repo made private after the fact disappears immediately.
- The repository-overview `url` is validated/canonicalized (`validate_github_url`) before
  querying — safe with raw query input, and a purely-private repo returns `404` (no
  existence disclosure).
- Star/visibility mutations require auth; visibility requires ownership.
- Private repositories, private analyses, and private chat sessions are never referenced by
  any public surface.

## Future improvements
- Follows / activity feed.
- Trending (stars over time).
- Collections / tags.
