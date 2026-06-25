"""User data access."""
from __future__ import annotations

from sqlalchemy import func, select

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_github_id(self, github_id: int) -> User | None:
        stmt = select(User).where(User.github_id == github_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Look up a user by their GitHub handle (case-insensitive).

        GitHub handles are unique at any point in time; if a handle was ever
        recycled we deterministically return the earliest-created account so a
        profile URL resolves stably.
        """
        stmt = (
            select(User)
            .where(func.lower(User.username) == username.lower())
            .order_by(User.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()


    async def upsert_from_github(
        self,
        *,
        github_id: int,
        username: str,
        display_name: str | None,
        email: str | None,
        avatar_url: str | None,
    ) -> User:
        """Create the user on first login, or refresh their profile fields."""
        user = await self.get_by_github_id(github_id)
        if user is None:
            user = User(
                github_id=github_id,
                username=username,
                display_name=display_name,
                email=email,
                avatar_url=avatar_url,
            )
            return await self.add(user)

        user.username = username
        user.display_name = display_name
        user.email = email
        user.avatar_url = avatar_url
        await self.session.flush()
        return user
