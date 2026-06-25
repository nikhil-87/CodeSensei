"""Authentication endpoints — GitHub OAuth login, session, logout.

Cookie strategy
---------------
The session is an httpOnly cookie holding a signed JWT (see ``app.core.auth``).
``httpOnly`` keeps it out of reach of XSS, ``SameSite=Lax`` is sufficient
because login is a top-level redirect (not a cross-site fetch), and ``secure``
is enabled in production so the cookie only travels over HTTPS.

A short-lived ``oauth_state`` cookie carries the anti-CSRF ``state`` between
the login redirect and the callback.
"""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Query, Request, Response, status
from fastapi.responses import RedirectResponse

from app.core.auth import create_session_token
from app.core.dependencies import (
    AuthServiceDep,
    CurrentUserDep,
    SettingsDep,
    UserRepoDep,
)
from app.core.exceptions import NotFoundError, UnauthorizedError
from app.schemas.auth import DevLoginRequest, UserRead

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_OAUTH_STATE_COOKIE = "codesensei_oauth_state"
_STATE_TTL_SECONDS = 600  # 10 minutes to complete the round-trip


def _set_session_cookie(response: Response, settings: SettingsDep, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


def _clear_session_cookie(response: Response, settings: SettingsDep) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )


@router.get(
    "/github/login",
    summary="Begin GitHub OAuth login (redirect to GitHub)",
)
async def github_login(
    auth_service: AuthServiceDep,
    settings: SettingsDep,
) -> RedirectResponse:
    if not settings.github_oauth_enabled:
        raise UnauthorizedError("GitHub OAuth is not configured on this server")

    state = auth_service.new_state()
    redirect = RedirectResponse(
        url=auth_service.authorize_url(state=state),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    # Stash the state in a short-lived httpOnly cookie to verify on callback.
    redirect.set_cookie(
        key=_OAUTH_STATE_COOKIE,
        value=state,
        max_age=_STATE_TTL_SECONDS,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
        path="/",
    )
    return redirect


@router.get(
    "/github/callback",
    summary="GitHub OAuth callback — exchange code, set session, redirect home",
)
async def github_callback(
    request: Request,
    auth_service: AuthServiceDep,
    settings: SettingsDep,
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    expected_state = request.cookies.get(_OAUTH_STATE_COOKIE)
    if not expected_state or expected_state != state:
        raise UnauthorizedError("Invalid OAuth state")

    user = await auth_service.exchange_code(code=code)
    token = create_session_token(
        settings, user_id=user.id, github_login=user.username
    )

    redirect = RedirectResponse(
        url=settings.frontend_base_url,
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )
    _set_session_cookie(redirect, settings, token)
    redirect.delete_cookie(_OAUTH_STATE_COOKIE, path="/")
    logger.info("user_logged_in", user_id=str(user.id), username=user.username)
    return redirect


@router.get(
    "/me",
    response_model=UserRead,
    summary="Return the currently authenticated user",
)
async def get_me(user: CurrentUserDep) -> UserRead:
    return UserRead.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the session cookie",
)
async def logout(settings: SettingsDep) -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_session_cookie(response, settings)
    return response


@router.post(
    "/dev-login",
    response_model=UserRead,
    summary="Password-less login for local development (404 in production)",
)
async def dev_login(
    payload: DevLoginRequest,
    settings: SettingsDep,
    user_repo: UserRepoDep,
    response: Response,
) -> UserRead:
    # Hard gate: this endpoint does not exist outside development/test.
    if not settings.dev_login_enabled:
        raise NotFoundError("Not found")

    username = payload.username.strip() or "dev-user"
    # Derive a deterministic fake GitHub id from the handle so repeated
    # dev-logins map to the same account.
    fake_github_id = -(abs(hash(username)) % 1_000_000_000) - 1
    user = await user_repo.upsert_from_github(
        github_id=fake_github_id,
        username=username,
        display_name=f"{username} (dev)",
        email=None,
        avatar_url=None,
    )
    token = create_session_token(
        settings, user_id=user.id, github_login=user.username
    )
    _set_session_cookie(response, settings, token)
    logger.info("dev_login", user_id=str(user.id), username=user.username)
    return UserRead.model_validate(user)
