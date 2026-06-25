"""RepositoryService — submission, listing, retrieval, refresh."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from app.core.config import Settings
from app.core.exceptions import (
    AnalysisAlreadyRunningError,
    RepositoryAlreadyExistsError,
    RepositoryNotFoundError,
)
from app.core.security import validate_branch_name, validate_github_url
from app.models.analysis_job import AnalysisJob, AnalysisJobStatus
from app.models.repository import Repository, RepositoryStatus
from app.repositories.analysis_job_repository import AnalysisJobRepository
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import RepositoryCreate
from app.workers.job_dispatcher import JobDispatcher

if TYPE_CHECKING:
    from app.schemas.discover import (
        DiscoverRepositoryRead,
        RepositoryGroupDetail,
    )
    from app.schemas.repository import RepositoryFreshness, RepositoryRead


class RepositoryService:
    def __init__(
        self,
        repository_repo: RepositoryRepository,
        job_repo: AnalysisJobRepository,
        dispatcher: JobDispatcher,
        settings: Settings,
    ) -> None:
        self._repos = repository_repo
        self._jobs = job_repo
        self._dispatcher = dispatcher
        self._settings = settings

    # ----- mapping --------------------------------------------------------
    def _freshness(self, repo: Repository) -> "RepositoryFreshness":
        """Freshness verdict for a stored analysis vs. the current pipeline."""
        from app.schemas.repository import RepositoryFreshness
        from shared.config.analysis_version import evaluate_freshness

        verdict = evaluate_freshness(
            is_ready=repo.status == RepositoryStatus.READY,
            analysis_version=repo.analysis_version,
            pipeline_version=repo.pipeline_version,
            schema_version=repo.schema_version,
            embedding_model=repo.embedding_model,
            current_embedding_model=self._settings.embedding_signature,
        )
        return RepositoryFreshness(
            state=verdict.state,
            reasons=list(verdict.reasons),
            affected_features=list(verdict.affected_features),
            can_refresh=verdict.can_refresh,
        )

    def to_read_model(self, repo: Repository) -> "RepositoryRead":
        """Map a Repository ORM row to its read DTO, attaching a freshness
        verdict computed against the *current* analysis pipeline versions.

        Centralized here so every read path (get, list, detail) reports
        staleness consistently instead of silently serving outdated data.
        """
        from app.schemas.repository import RepositoryRead

        model = RepositoryRead.model_validate(repo)
        model.freshness = self._freshness(repo)
        return model

    def to_read_models_with_stars(
        self, repos: list[Repository], *, starred_ids: set[uuid.UUID]
    ) -> list["RepositoryRead"]:
        """Map a list of repos, flagging which the current viewer has starred.

        ``starred_ids`` is the (pre-computed, batched) subset of these repos'
        ids the viewer stars — pass an empty set for anonymous callers.
        """
        models = []
        for repo in repos:
            model = self.to_read_model(repo)
            model.viewer_has_starred = repo.id in starred_ids
            models.append(model)
        return models

    # ----- write paths ----------------------------------------------------
    async def submit(
        self, payload: RepositoryCreate, *, owner_id: uuid.UUID
    ) -> tuple[Repository, AnalysisJob]:
        canonical_url = validate_github_url(str(payload.url))
        branch = validate_branch_name(payload.branch)

        owner, name = canonical_url.rsplit("/", 2)[-2:]

        existing = await self._repos.get_by_url(
            canonical_url, branch, owner_id=owner_id
        )
        if existing is not None:
            # The caller already has this repository. Never create a duplicate
            # row, and never silently re-analyze — surface a conflict so the UI
            # can offer "Open existing" vs. "Refresh". An in-flight job is a
            # distinct, more specific conflict.
            if await self._jobs.has_active_job(existing.id):
                raise AnalysisAlreadyRunningError(
                    "This repository is already being analyzed.",
                    details={"repository_id": str(existing.id)},
                )
            raise RepositoryAlreadyExistsError(
                "You have already analyzed this repository. Refresh it to get "
                "the latest insights based on the current repository state.",
                details={"repository_id": str(existing.id)},
            )

        repo = Repository(
            url=canonical_url,
            branch=branch,
            name=name,
            owner=owner,
            owner_id=owner_id,
            status=RepositoryStatus.PENDING,
        )
        repo = await self._repos.add(repo)

        job = AnalysisJob(
            repository_id=repo.id,
            status=AnalysisJobStatus.QUEUED,
            queued_at=datetime.now(UTC),
        )
        job = await self._jobs.add_active(job)

        rq_job_id = self._dispatcher.enqueue_analysis(repo.id, job.id)
        job.rq_job_id = rq_job_id

        return repo, job

    # ----- read paths -----------------------------------------------------
    async def get(self, repository_id: uuid.UUID) -> Repository:
        repo = await self._repos.get(repository_id)
        if repo is None:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")
        return repo

    async def get_for_user(
        self, repository_id: uuid.UUID, *, user_id: uuid.UUID | None
    ) -> Repository:
        """Fetch a repository the caller is allowed to *read*.

        Allowed when the caller owns it, or when it is public. Anything else
        raises ``RepositoryNotFoundError`` (a 404) so we never disclose the
        existence of repositories the caller cannot see.
        """
        repo = await self.get(repository_id)
        is_owner = (
            user_id is not None
            and repo.owner_id is not None
            and repo.owner_id == user_id
        )
        if is_owner or repo.is_public:
            return repo
        raise RepositoryNotFoundError(f"Repository {repository_id} not found")

    async def list(
        self,
        *,
        page: int,
        page_size: int,
        owner_id: uuid.UUID,
        status: RepositoryStatus | None = None,
    ) -> tuple[list[Repository], int]:
        offset = (page - 1) * page_size
        return await self._repos.list_paginated(
            limit=page_size, offset=offset, status=status, owner_id=owner_id
        )

    async def list_public(
        self,
        *,
        page: int,
        page_size: int,
        sort: str = "stars",
        query: str | None = None,
        language: str | None = None,
    ) -> tuple[list[Repository], int]:
        """Public, analyzed repositories for the discovery hub."""
        offset = (page - 1) * page_size
        return await self._repos.list_public(
            limit=page_size,
            offset=offset,
            sort=sort,
            query=query,
            language=language,
        )

    async def list_public_grouped(
        self,
        *,
        page: int,
        page_size: int,
        sort: str = "stars",
        query: str | None = None,
        language: str | None = None,
    ) -> tuple[list["DiscoverRepositoryRead"], int]:
        """Repository-centric discovery: one entry per ``(url, branch)``,
        collapsing the multiple public analyses of the same repository.
        """
        from app.schemas.discover import DiscoverRepositoryRead

        offset = (page - 1) * page_size
        rows, total = await self._repos.list_public_grouped(
            limit=page_size, offset=offset, sort=sort, query=query, language=language
        )
        items = [
            DiscoverRepositoryRead(
                url=r["url"],
                branch=r["branch"],
                name=r["name"],
                owner=r["owner"],
                analyses_count=int(r["analyses_count"]),
                total_stars=int(r["group_stars"]),
                latest_analyzed_at=r["analyzed_at"],
                languages=r["languages"],
                file_count=int(r["file_count"]),
                total_lines=int(r["total_lines"]),
                latest_repository_id=r["repo_id"],
            )
            for r in rows
        ]
        return items, total

    async def public_repository_group(
        self,
        *,
        url: str,
        branch: str | None,
        starred_ids: set[uuid.UUID],
    ) -> "RepositoryGroupDetail":
        """The repository overview: header + every public analysis of a single
        ``(url, branch)`` repository. ``url`` is validated/canonicalized so this
        is safe to call with raw query input.

        Raises ``RepositoryNotFoundError`` when no public analysis exists, so we
        never confirm the existence of a purely-private repository.
        """
        from app.schemas.discover import (
            AnalystRef,
            PublicAnalysisRead,
            RepositoryGroupDetail,
        )

        canonical_url = validate_github_url(url)
        normalized_branch = validate_branch_name(branch)
        repos = await self._repos.list_public_group(canonical_url, normalized_branch)
        if not repos:
            raise RepositoryNotFoundError("No public analysis found for this repository")

        latest = repos[0]
        total_stars = sum(r.star_count for r in repos)
        analyses = [
            PublicAnalysisRead(
                repository_id=r.id,
                analyst=AnalystRef(
                    username=r.owner_user.username if r.owner_user else None,
                    display_name=r.owner_user.display_name if r.owner_user else None,
                    avatar_url=r.owner_user.avatar_url if r.owner_user else None,
                ),
                analyzed_at=r.analyzed_at,
                star_count=r.star_count,
                viewer_has_starred=r.id in starred_ids,
                analysis_version=r.analysis_version,
                pipeline_version=r.pipeline_version,
                schema_version=r.schema_version,
                file_count=r.file_count,
                total_lines=r.total_lines,
                languages=r.languages,
                freshness=self._freshness(r),
            )
            for r in repos
        ]
        return RepositoryGroupDetail(
            url=canonical_url,
            branch=normalized_branch,
            name=latest.name,
            owner=latest.owner,
            analyses_count=len(repos),
            total_stars=total_stars,
            latest_analyzed_at=latest.analyzed_at,
            analyses=analyses,
        )

    async def delete(
        self, repository_id: uuid.UUID, *, owner_id: uuid.UUID
    ) -> None:
        repo = await self._require_owned(repository_id, owner_id=owner_id)
        await self._repos.delete(repo)

    async def set_visibility(
        self, repository_id: uuid.UUID, *, owner_id: uuid.UUID, is_public: bool
    ) -> Repository:
        repo = await self._require_owned(repository_id, owner_id=owner_id)
        repo.is_public = is_public
        return repo

    # ----- helpers --------------------------------------------------------
    async def _require_owned(
        self, repository_id: uuid.UUID, *, owner_id: uuid.UUID
    ) -> Repository:
        """Load a repository only if ``owner_id`` owns it; else 404."""
        repo = await self._repos.get(repository_id)
        if repo is None or repo.owner_id != owner_id:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")
        return repo
