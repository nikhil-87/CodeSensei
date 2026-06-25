"""Repository data access."""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import asc, desc, func, or_, select

from app.models.repository import Repository, RepositoryStatus
from app.repositories.base import BaseRepository


def _apply_public_order(stmt, sort: str):  # noqa: ANN001 - SQLAlchemy Select
    """Order a public-repository query. Falls back to most-starred."""
    if sort == "recent":
        return stmt.order_by(
            desc(Repository.analyzed_at), desc(Repository.created_at)
        )
    if sort == "name":
        return stmt.order_by(asc(Repository.name), asc(Repository.owner))
    # Default: most popular, tie-broken by recency.
    return stmt.order_by(
        desc(Repository.star_count), desc(Repository.analyzed_at)
    )


class RepositoryRepository(BaseRepository[Repository]):
    model = Repository

    async def get_by_url(
        self, url: str, branch: str | None, *, owner_id: uuid.UUID | None = None
    ) -> Repository | None:
        stmt = select(Repository).where(
            Repository.url == url,
            Repository.branch.is_(branch) if branch is None else Repository.branch == branch,
        )
        # Scope to the owner so each user gets their own copy of a given URL.
        stmt = stmt.where(
            Repository.owner_id.is_(None)
            if owner_id is None
            else Repository.owner_id == owner_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_paginated(
        self,
        *,
        limit: int,
        offset: int,
        status: RepositoryStatus | None = None,
        owner: str | None = None,
        owner_id: uuid.UUID | None = None,
    ) -> tuple[list[Repository], int]:
        base_stmt = select(Repository)
        count_stmt = select(func.count()).select_from(Repository)
        if status is not None:
            base_stmt = base_stmt.where(Repository.status == status)
            count_stmt = count_stmt.where(Repository.status == status)
        if owner is not None:
            base_stmt = base_stmt.where(Repository.owner == owner)
            count_stmt = count_stmt.where(Repository.owner == owner)
        if owner_id is not None:
            base_stmt = base_stmt.where(Repository.owner_id == owner_id)
            count_stmt = count_stmt.where(Repository.owner_id == owner_id)

        base_stmt = base_stmt.order_by(desc(Repository.created_at)).limit(limit).offset(offset)
        result = await self.session.execute(base_stmt)
        items = list(result.scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total

    async def list_public(
        self,
        *,
        limit: int,
        offset: int,
        sort: str = "stars",
        query: str | None = None,
        language: str | None = None,
    ) -> tuple[list[Repository], int]:
        """Public, fully-analyzed repositories for the discovery hub.

        Only ``READY`` public repos are surfaced — a repo that is public but
        still analyzing isn't useful to browse yet.
        """
        base_stmt = select(Repository).where(
            Repository.is_public.is_(True),
            Repository.status == RepositoryStatus.READY,
        )
        count_stmt = (
            select(func.count())
            .select_from(Repository)
            .where(
                Repository.is_public.is_(True),
                Repository.status == RepositoryStatus.READY,
            )
        )

        if query:
            like = f"%{query}%"
            term = or_(Repository.name.ilike(like), Repository.owner.ilike(like))
            base_stmt = base_stmt.where(term)
            count_stmt = count_stmt.where(term)

        if language:
            # languages is a denormalized "lang:count,lang:count" string. Match
            # the token at a boundary so "java" does not match "javascript".
            head = f"{language}:%"
            mid = f"%,{language}:%"
            term = or_(
                Repository.languages.ilike(head),
                Repository.languages.ilike(mid),
            )
            base_stmt = base_stmt.where(term)
            count_stmt = count_stmt.where(term)

        base_stmt = _apply_public_order(base_stmt, sort).limit(limit).offset(offset)
        items = list((await self.session.execute(base_stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total

    async def list_public_for_owner(
        self,
        *,
        owner_id: uuid.UUID,
        limit: int,
        offset: int,
        sort: str = "stars",
    ) -> tuple[list[Repository], int]:
        """A user's public, analyzed repositories — backs their profile page."""
        base_stmt = select(Repository).where(
            Repository.owner_id == owner_id,
            Repository.is_public.is_(True),
            Repository.status == RepositoryStatus.READY,
        )
        count_stmt = (
            select(func.count())
            .select_from(Repository)
            .where(
                Repository.owner_id == owner_id,
                Repository.is_public.is_(True),
                Repository.status == RepositoryStatus.READY,
            )
        )
        base_stmt = _apply_public_order(base_stmt, sort).limit(limit).offset(offset)
        items = list((await self.session.execute(base_stmt)).scalars().all())
        total = int((await self.session.execute(count_stmt)).scalar_one())
        return items, total

    async def public_stats_for_owner(self, owner_id: uuid.UUID) -> tuple[int, int]:
        """``(public_repository_count, total_stars_received)`` for a profile."""
        stmt = select(
            func.count(Repository.id),
            func.coalesce(func.sum(Repository.star_count), 0),
        ).where(
            Repository.owner_id == owner_id,
            Repository.is_public.is_(True),
            Repository.status == RepositoryStatus.READY,
        )
        row = (await self.session.execute(stmt)).one()
        return int(row[0]), int(row[1])

    async def list_public_grouped(
        self,
        *,
        limit: int,
        offset: int,
        sort: str = "stars",
        query: str | None = None,
        language: str | None = None,
    ) -> tuple[list[dict], int]:
        """Repository-centric discovery: collapse public analyses that share a
        ``(url, branch)`` into a single group.

        Multiple users can each analyze the same repository and make it public;
        Discover should list the *repository* once, not once per analysis. We
        pick the most-recent analysis as the group's representative (for display
        fields) and attach ``analyses_count`` + ``total_stars`` over the group.
        """
        public = (
            Repository.is_public.is_(True),
            Repository.status == RepositoryStatus.READY,
        )
        filters = list(public)
        if query:
            like = f"%{query}%"
            filters.append(or_(Repository.name.ilike(like), Repository.owner.ilike(like)))
        if language:
            head = f"{language}:%"
            mid = f"%,{language}:%"
            filters.append(
                or_(
                    Repository.languages.ilike(head),
                    Repository.languages.ilike(mid),
                )
            )

        part = (Repository.url, Repository.branch)
        rn = func.row_number().over(
            partition_by=part,
            order_by=(
                desc(Repository.analyzed_at),
                desc(Repository.created_at),
            ),
        ).label("rn")
        analyses_count = func.count().over(partition_by=part).label("analyses_count")
        group_stars = func.coalesce(
            func.sum(Repository.star_count).over(partition_by=part), 0
        ).label("group_stars")

        inner = (
            select(
                Repository.id.label("repo_id"),
                Repository.url.label("url"),
                Repository.branch.label("branch"),
                Repository.name.label("name"),
                Repository.owner.label("owner"),
                Repository.languages.label("languages"),
                Repository.file_count.label("file_count"),
                Repository.total_lines.label("total_lines"),
                Repository.analyzed_at.label("analyzed_at"),
                rn,
                analyses_count,
                group_stars,
            )
            .where(*filters)
            .subquery()
        )

        stmt = select(inner).where(inner.c.rn == 1)
        if sort == "recent":
            stmt = stmt.order_by(desc(inner.c.analyzed_at))
        elif sort == "name":
            stmt = stmt.order_by(asc(inner.c.name), asc(inner.c.owner))
        else:  # stars (default): most popular repository, tie-broken by recency
            stmt = stmt.order_by(desc(inner.c.group_stars), desc(inner.c.analyzed_at))
        stmt = stmt.limit(limit).offset(offset)

        rows = (await self.session.execute(stmt)).mappings().all()

        # Total = number of distinct (url, branch) groups in the filtered set.
        group_subq = (
            select(Repository.url, Repository.branch)
            .where(*filters)
            .group_by(Repository.url, Repository.branch)
            .subquery()
        )
        total = int(
            (
                await self.session.execute(
                    select(func.count()).select_from(group_subq)
                )
            ).scalar_one()
        )
        return [dict(r) for r in rows], total

    async def list_public_group(
        self, url: str, branch: str | None
    ) -> list[Repository]:
        """All public, analyzed copies of a single ``(url, branch)`` repository,
        newest analysis first, with each analysis's owner eagerly loaded.

        Backs the repository overview / analysis-history page. Only public,
        READY rows are returned so private analyses never leak.
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(Repository)
            .options(joinedload(Repository.owner_user))
            .where(
                Repository.url == url,
                Repository.branch.is_(branch)
                if branch is None
                else Repository.branch == branch,
                Repository.is_public.is_(True),
                Repository.status == RepositoryStatus.READY,
            )
            .order_by(desc(Repository.analyzed_at), desc(Repository.created_at))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().unique().all())


    async def update_status(
        self,
        repository_id: uuid.UUID,
        status: RepositoryStatus,
        *,
        error_message: str | None = None,
        analyzed_at: datetime | None = None,
    ) -> Repository | None:
        repo = await self.get(repository_id)
        if repo is None:
            return None
        repo.status = status
        if error_message is not None:
            repo.error_message = error_message
        if analyzed_at is not None:
            repo.analyzed_at = analyzed_at
        await self.session.flush()
        return repo
