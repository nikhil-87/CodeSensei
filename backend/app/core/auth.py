"""Authentication primitives: JWT session tokens + cookie helpers.

We keep sessions stateless: a short JSON Web Token (HS256, signed with the
application secret) is stored in an httpOnly cookie. There is no server-side
session store to invalidate — logout simply clears the cookie. This is a
deliberate trade-off for a small app: simple, horizontally scalable, and
auditable on a resume without dragging in a session backend.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.core.config import Settings

_ALGORITHM = "HS256"


def create_session_token(
    settings: Settings,
    *,
    user_id: uuid.UUID,
    github_login: str,
) -> str:
    """Mint a signed session JWT for an authenticated user."""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "gh": github_login,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.session_ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=_ALGORITHM)


def decode_session_token(settings: Settings, token: str) -> dict[str, Any] | None:
    """Return the JWT claims, or ``None`` if the token is invalid/expired."""
    try:
        return jwt.decode(token, settings.app_secret_key, algorithms=[_ALGORITHM])
    except jwt.PyJWTError:
        return None
