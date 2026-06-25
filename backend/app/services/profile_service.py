"""ProfileService — read-only public profiles at ``/users/{username}``.

Serves anonymous visitors, so it exposes only public-safe fields and only a
user's *public, analyzed* repositories. A missing handle is a 404.
"""
from __future__ import annotations

from app.core.exceptions import UserNotFoundError
from app.models.repository import Repository
from app.models.user import User
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.user_repository import UserRepository
from app.schemas.profile import PublicProfileRead


class ProfileService:
    def __init__(
        self,
        user_repo: UserRepository,
        repository_repo: RepositoryRepository,
    ) -> None:
        self._users = user_repo
        self._repos = repository_repo

    async def _resolve(self, username: str) -> User:
        user = await self._users.get_by_username(username)
        if user is None:
            raise UserNotFoundError(f"No user found for '{username}'")
        return user

    async def get_profile(self, username: str) -> PublicProfileRead:
        user = await self._resolve(username)
        repo_count, total_stars = await self._repos.public_stats_for_owner(user.id)
        return PublicProfileRead(
            username=user.username,
            display_name=user.display_name,
            avatar_url=user.avatar_url,
            public_repository_count=repo_count,
            total_stars=total_stars,
        )

    async def list_public_repositories(
        self,
        username: str,
        *,
        page: int,
        page_size: int,
        sort: str = "stars",
    ) -> tuple[list[Repository], int]:
        user = await self._resolve(username)
        offset = (page - 1) * page_size
        return await self._repos.list_public_for_owner(
            owner_id=user.id, limit=page_size, offset=offset, sort=sort
        )
