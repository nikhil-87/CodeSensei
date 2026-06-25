"""Chat session endpoints — persistent, user-private AI conversations.

Two route groups:

* ``/repositories/{repository_id}/chat-sessions`` — create + list sessions for
  a repo. Authorized by *read* access to the repo (owner or public), because a
  signed-in user may chat about any repository they can see and keep their
  conversations private.
* ``/chat-sessions/{session_id}`` — get / rename / delete / messages / chat.
  Authorized strictly by ownership; non-owners get a 404 (IDOR-safe), never a
  hint that the session exists.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, status
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import (
    ChatSessionServiceDep,
    CurrentUserDep,
    RepositoryServiceDep,
)
from app.schemas.chat import (
    ChatMessageRead,
    ChatSessionCreate,
    ChatSessionRead,
    ChatSessionUpdate,
    SessionChatRequest,
)
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["chat-sessions"])


# ---------------------------------------------------------------------------
# Repository-scoped: create + list
# ---------------------------------------------------------------------------
@router.post(
    "/repositories/{repository_id}/chat-sessions",
    response_model=ChatSessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new AI chat session for a repository",
)
async def create_session(
    repository_id: uuid.UUID,
    payload: ChatSessionCreate,
    user: CurrentUserDep,
    chat_service: ChatSessionServiceDep,
    repo_service: RepositoryServiceDep,
) -> ChatSessionRead:
    # Must be able to *read* the repo (owner or public) — 404 otherwise.
    await repo_service.get_for_user(repository_id, user_id=user.id)
    session = await chat_service.create_session(
        user_id=user.id, repository_id=repository_id, title=payload.title
    )
    return ChatSessionRead.model_validate(session)


@router.get(
    "/repositories/{repository_id}/chat-sessions",
    response_model=PaginatedResponse[ChatSessionRead],
    summary="List my chat sessions for a repository",
)
async def list_sessions(
    repository_id: uuid.UUID,
    user: CurrentUserDep,
    chat_service: ChatSessionServiceDep,
    repo_service: RepositoryServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> PaginatedResponse[ChatSessionRead]:
    await repo_service.get_for_user(repository_id, user_id=user.id)
    sessions, total = await chat_service.list_sessions(
        user_id=user.id,
        repository_id=repository_id,
        page=page,
        page_size=page_size,
    )
    return PaginatedResponse[ChatSessionRead](
        items=[ChatSessionRead.model_validate(s) for s in sessions],
        page=page,
        page_size=page_size,
        total=total,
    )


# ---------------------------------------------------------------------------
# Session-scoped: get / rename / delete / messages / chat
# ---------------------------------------------------------------------------
@router.get(
    "/chat-sessions/{session_id}",
    response_model=ChatSessionRead,
    summary="Get a chat session",
)
async def get_session(
    session_id: uuid.UUID,
    user: CurrentUserDep,
    chat_service: ChatSessionServiceDep,
) -> ChatSessionRead:
    session = await chat_service.get_session(session_id, user_id=user.id)
    return ChatSessionRead.model_validate(session)


@router.patch(
    "/chat-sessions/{session_id}",
    response_model=ChatSessionRead,
    summary="Rename a chat session",
)
async def rename_session(
    session_id: uuid.UUID,
    payload: ChatSessionUpdate,
    user: CurrentUserDep,
    chat_service: ChatSessionServiceDep,
) -> ChatSessionRead:
    session = await chat_service.rename_session(
        session_id, user_id=user.id, title=payload.title
    )
    return ChatSessionRead.model_validate(session)


@router.delete(
    "/chat-sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a chat session",
)
async def delete_session(
    session_id: uuid.UUID,
    user: CurrentUserDep,
    chat_service: ChatSessionServiceDep,
) -> None:
    await chat_service.delete_session(session_id, user_id=user.id)


@router.get(
    "/chat-sessions/{session_id}/messages",
    response_model=PaginatedResponse[ChatMessageRead],
    summary="List messages in a chat session",
)
async def list_messages(
    session_id: uuid.UUID,
    user: CurrentUserDep,
    chat_service: ChatSessionServiceDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=200),
) -> PaginatedResponse[ChatMessageRead]:
    messages, total = await chat_service.list_messages(
        session_id, user_id=user.id, page=page, page_size=page_size
    )
    return PaginatedResponse[ChatMessageRead](
        items=[ChatMessageRead.model_validate(m) for m in messages],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post(
    "/chat-sessions/{session_id}/chat",
    summary="Send a message and stream the assistant's answer (SSE)",
)
async def chat(
    session_id: uuid.UUID,
    payload: SessionChatRequest,
    user: CurrentUserDep,
    chat_service: ChatSessionServiceDep,
    repo_service: RepositoryServiceDep,
) -> EventSourceResponse:
    # Ownership (404 if not mine) ...
    session = await chat_service.get_session(session_id, user_id=user.id)
    # ... and the repo must still be readable by me (it may have gone private).
    await repo_service.get_for_user(session.repository_id, user_id=user.id)

    return EventSourceResponse(
        chat_service.stream_chat(session_id, user_id=user.id, request=payload)
    )
