"""StarService — toggle stars and keep the denormalized counter consistent.

Authorization note: visibility is enforced by the *endpoint* (which loads the
repository via :meth:`RepositoryService.get_for_user`, a 404 for repos the
caller cannot see). This service therefore receives an already-authorized
``Repository`` and concerns itself only with star bookkeeping.

The ``repositories.star_count`` counter is recomputed from the authoritative
``stars`` rows on every toggle rather than blindly incremented, so it cannot
drift out of sync even under concurrent or repeated requests (idempotent).
"""
from __future__ import annotations

import uuid

from app.models.repository import Repository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.star_repository import StarRepository


class StarService:
    def __init__(
        self,
        star_repo: StarRepository,
        repository_repo: RepositoryRepository,
    ) -> None:
        self._stars = star_repo
        self._repos = repository_repo

    async def star(self, repo: Repository, *, user_id: uuid.UUID) -> int:
        """Star ``repo`` for ``user_id`` (idempotent). Returns the new count."""
        await self._stars.create_star(user_id=user_id, repository_id=repo.id)
        return await self._sync_count(repo)

    async def unstar(self, repo: Repository, *, user_id: uuid.UUID) -> int:
        """Remove ``user_id``'s star from ``repo`` (idempotent)."""
        await self._stars.delete_star(user_id=user_id, repository_id=repo.id)
        return await self._sync_count(repo)

    async def is_starred(
        self, *, user_id: uuid.UUID, repository_id: uuid.UUID
    ) -> bool:
        return await self._stars.exists(
            user_id=user_id, repository_id=repository_id
        )

    async def starred_ids(
        self, *, user_id: uuid.UUID, repository_ids: list[uuid.UUID]
    ) -> set[uuid.UUID]:
        return await self._stars.starred_repository_ids(
            user_id=user_id, repository_ids=repository_ids
        )

    async def list_starred(
        self, *, user_id: uuid.UUID, page: int, page_size: int
    ) -> tuple[list[Repository], int]:
        offset = (page - 1) * page_size
        return await self._stars.list_starred(
            user_id=user_id, limit=page_size, offset=offset
        )

    # ----- helpers --------------------------------------------------------
    async def _sync_count(self, repo: Repository) -> int:
        """Recompute the denormalized counter from the source-of-truth rows."""
        count = await self._stars.count_for_repository(repo.id)
        repo.star_count = count
        return count
