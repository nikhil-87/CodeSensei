"""AuthService — GitHub OAuth handshake + user provisioning.

Flow (Authorization Code grant):

1. ``authorize_url`` builds the GitHub consent URL with an anti-CSRF ``state``.
2. GitHub redirects back with ``?code=...&state=...``.
3. ``exchange_code`` swaps the code for an access token, then reads the user's
   public profile, and upserts a local :class:`User`.

The access token is used once to read the profile and then discarded — we do
not store GitHub tokens (nothing in this app calls the GitHub API on the
user's behalf after login).
"""
from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx
import structlog

from app.core.config import Settings
from app.core.exceptions import ExternalServiceError, UnauthorizedError
from app.models.user import User
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)

_GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"
_OAUTH_SCOPE = "read:user user:email"
_HTTP_TIMEOUT = httpx.Timeout(10.0)


class AuthService:
    def __init__(self, user_repo: UserRepository, settings: Settings) -> None:
        self._users = user_repo
        self._settings = settings

    # ----- step 1: consent URL -------------------------------------------
    @staticmethod
    def new_state() -> str:
        return secrets.token_urlsafe(32)

    def authorize_url(self, *, state: str) -> str:
        params = {
            "client_id": self._settings.github_oauth_client_id,
            "redirect_uri": self._settings.github_oauth_callback_url,
            "scope": _OAUTH_SCOPE,
            "state": state,
            "allow_signup": "true",
        }
        return f"{_GITHUB_AUTHORIZE_URL}?{urlencode(params)}"

    # ----- step 3: code -> token -> profile -> user ----------------------
    async def exchange_code(self, *, code: str) -> User:
        async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
            access_token = await self._fetch_access_token(client, code=code)
            profile = await self._fetch_profile(client, access_token=access_token)
            email = profile.get("email") or await self._fetch_primary_email(
                client, access_token=access_token
            )

        return await self._users.upsert_from_github(
            github_id=int(profile["id"]),
            username=str(profile["login"]),
            display_name=profile.get("name"),
            email=email,
            avatar_url=profile.get("avatar_url"),
        )

    async def _fetch_access_token(
        self, client: httpx.AsyncClient, *, code: str
    ) -> str:
        resp = await client.post(
            _GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": self._settings.github_oauth_client_id,
                "client_secret": self._settings.github_oauth_client_secret,
                "code": code,
                "redirect_uri": self._settings.github_oauth_callback_url,
            },
        )
        if resp.status_code != 200:
            logger.warning("github_token_exchange_failed", status=resp.status_code)
            raise ExternalServiceError("GitHub token exchange failed")
        body = resp.json()
        token = body.get("access_token")
        if not token:
            # GitHub returns 200 with an `error` field on bad/expired codes.
            logger.warning("github_token_missing", error=body.get("error"))
            raise UnauthorizedError("GitHub did not return an access token")
        return str(token)

    async def _fetch_profile(
        self, client: httpx.AsyncClient, *, access_token: str
    ) -> dict:
        resp = await client.get(
            _GITHUB_USER_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {access_token}",
            },
        )
        if resp.status_code != 200:
            logger.warning("github_profile_fetch_failed", status=resp.status_code)
            raise ExternalServiceError("Failed to read GitHub profile")
        return resp.json()

    async def _fetch_primary_email(
        self, client: httpx.AsyncClient, *, access_token: str
    ) -> str | None:
        """Best-effort: profile email is null unless made public."""
        try:
            resp = await client.get(
                _GITHUB_EMAILS_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {access_token}",
                },
            )
        except httpx.HTTPError:
            return None
        if resp.status_code != 200:
            return None
        for entry in resp.json():
            if entry.get("primary") and entry.get("email"):
                return str(entry["email"])
        return None
