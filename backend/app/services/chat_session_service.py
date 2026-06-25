"""ChatSessionService — persistent, user-private AI conversations.

Two distinct transaction styles live here on purpose:

* **CRUD** (create / list / rename / delete / read messages) runs on the
  request-scoped session injected via DI. Short, transactional, ordinary.

* **Streaming chat** must persist the user turn *before* a potentially long
  LLM stream and the assistant turn *after* it. A request-scoped session is
  the wrong tool: FastAPI tears it down only once the streaming response is
  fully consumed, and a client disconnect would roll back the user's message.
  So streaming uses :func:`get_session_factory` to open two short, independent
  transactions that commit immediately and are unaffected by the stream's fate.

Ownership is enforced in SQL (``user_id`` filter) and surfaced as a 404 for
anything the caller doesn't own — a conversation is private to its owner even
when the underlying repository is public.
"""
from __future__ import annotations

import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.db.session import get_session_factory
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.repositories.chat_message_repository import ChatMessageRepository
from app.repositories.chat_session_repository import ChatSessionRepository
from app.schemas.ai import ChatMessage as ApiChatMessage
from app.schemas.ai import ChatRequest as ApiChatRequest
from app.schemas.chat import AttachedContext, SessionChatRequest
from app.services.ai_service import AIService

logger = structlog.get_logger(__name__)

# How many prior messages we feed back into the model. Bounds prompt size and
# cost regardless of how long a conversation grows.
MAX_HISTORY_MESSAGES = 20
# Sessions are created titleless; the first question names them.
_DEFAULT_TITLE = "New chat"
_TITLE_MAX = 200


class ChatSessionNotFoundError(NotFoundError):
    """Raised when a session doesn't exist or isn't owned by the caller."""


class ChatSessionService:
    def __init__(
        self,
        session_repo: ChatSessionRepository,
        message_repo: ChatMessageRepository,
        ai_service: AIService,
        settings: Settings,
    ) -> None:
        self._sessions = session_repo
        self._messages = message_repo
        self._ai = ai_service
        self._settings = settings

    # ------------------------------------------------------------------
    # CRUD (request-scoped session)
    # ------------------------------------------------------------------
    async def create_session(
        self,
        *,
        user_id: uuid.UUID,
        repository_id: uuid.UUID,
        title: str | None,
    ) -> ChatSession:
        session = ChatSession(
            user_id=user_id,
            repository_id=repository_id,
            title=(title or _DEFAULT_TITLE).strip()[:_TITLE_MAX] or _DEFAULT_TITLE,
        )
        return await self._sessions.add(session)

    async def list_sessions(
        self,
        *,
        user_id: uuid.UUID,
        repository_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[ChatSession], int]:
        offset = (page - 1) * page_size
        return await self._sessions.list_for_repository(
            user_id=user_id,
            repository_id=repository_id,
            limit=page_size,
            offset=offset,
        )

    async def get_session(
        self, session_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> ChatSession:
        session = await self._sessions.get_owned(session_id, user_id=user_id)
        if session is None:
            raise ChatSessionNotFoundError(f"Chat session {session_id} not found")
        return session

    async def rename_session(
        self, session_id: uuid.UUID, *, user_id: uuid.UUID, title: str
    ) -> ChatSession:
        session = await self.get_session(session_id, user_id=user_id)
        session.title = title.strip()[:_TITLE_MAX] or _DEFAULT_TITLE
        return session

    async def delete_session(
        self, session_id: uuid.UUID, *, user_id: uuid.UUID
    ) -> None:
        deleted = await self._sessions.delete_owned(session_id, user_id=user_id)
        if not deleted:
            raise ChatSessionNotFoundError(f"Chat session {session_id} not found")

    async def list_messages(
        self,
        session_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        page: int,
        page_size: int,
    ) -> tuple[list[ChatMessage], int]:
        # Ownership check first — never reveal another user's transcript.
        await self.get_session(session_id, user_id=user_id)
        offset = (page - 1) * page_size
        return await self._messages.list_for_session(
            session_id=session_id, limit=page_size, offset=offset
        )

    # ------------------------------------------------------------------
    # Streaming chat (decoupled short transactions)
    # ------------------------------------------------------------------
    async def stream_chat(
        self,
        session_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        request: SessionChatRequest,
    ) -> AsyncIterator[dict[str, str]]:
        """Persist the user turn, stream the answer, persist the assistant turn.

        Yields ``EventSourceResponse``-shaped dicts identical to the stateless
        ``/ai/chat`` contract, so the frontend renderer is reused verbatim.
        """
        # --- transaction 1: validate, load history, persist user turn -----
        try:
            repository_id, history = await self._begin_turn(
                session_id, user_id=user_id, request=request
            )
        except ChatSessionNotFoundError:
            yield _error_event("This conversation no longer exists.")
            yield _done_event()
            return

        api_request = ApiChatRequest(
            repository_id=repository_id,
            question=_augment(request.question, request.attached),
            history=history,
            top_k=request.top_k,
            attached_paths=[a.path for a in request.attached],
        )

        # --- stream, accumulating the assistant answer + citations --------
        answer_parts: list[str] = []
        citations: list[dict[str, Any]] = []
        saw_done = False
        try:
            async for sse in self._ai.stream_chat(api_request):
                event = sse.get("event")
                data = sse.get("data")
                if event == "token" and data:
                    parsed = _safe_json(data)
                    if parsed and parsed.get("content"):
                        answer_parts.append(str(parsed["content"]))
                elif event == "citations" and data:
                    parsed = _safe_json(data)
                    if parsed and parsed.get("citations"):
                        citations = list(parsed["citations"])
                elif event == "done":
                    saw_done = True
                yield sse
        except Exception as exc:  # noqa: BLE001 — defence in depth
            logger.warning("session_chat_stream_failed", error=str(exc))
            yield _error_event("The assistant ran into a problem. Please try again.")
            yield _done_event()
            saw_done = False

        # --- transaction 2: persist assistant turn (best-effort) ----------
        if saw_done and answer_parts:
            await self._finish_turn(
                session_id,
                user_id=user_id,
                content="".join(answer_parts),
                citations=citations or None,
            )

    # ------------------------------------------------------------------
    # streaming internals — each opens its own committed transaction
    # ------------------------------------------------------------------
    async def _begin_turn(
        self,
        session_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        request: SessionChatRequest,
    ) -> tuple[uuid.UUID, list[ApiChatMessage]]:
        factory = get_session_factory(self._settings)
        async with factory() as db:
            sessions = ChatSessionRepository(db)
            messages = ChatMessageRepository(db)

            session = await sessions.get_owned(session_id, user_id=user_id)
            if session is None:
                raise ChatSessionNotFoundError(f"Chat session {session_id} not found")

            repository_id = session.repository_id

            prior = await messages.recent_for_session(
                session_id=session_id, limit=MAX_HISTORY_MESSAGES
            )
            history = _to_api_history(prior)

            attached_payload = [a.model_dump() for a in request.attached] or None
            db.add(
                ChatMessage(
                    session_id=session_id,
                    role="user",
                    content=request.question,
                    attached_context=attached_payload,
                )
            )

            # First real question names an untitled conversation.
            if session.title == _DEFAULT_TITLE:
                session.title = _derive_title(request.question)
            session.last_activity_at = datetime.now(UTC)

            await db.commit()
            return repository_id, history

    async def _finish_turn(
        self,
        session_id: uuid.UUID,
        *,
        user_id: uuid.UUID,
        content: str,
        citations: list[dict[str, Any]] | None,
    ) -> None:
        factory = get_session_factory(self._settings)
        try:
            async with factory() as db:
                sessions = ChatSessionRepository(db)
                # Session may have been deleted mid-stream — skip silently.
                session = await sessions.get_owned(session_id, user_id=user_id)
                if session is None:
                    return
                db.add(
                    ChatMessage(
                        session_id=session_id,
                        role="assistant",
                        content=content,
                        citations=citations,
                    )
                )
                session.last_activity_at = datetime.now(UTC)
                await db.commit()
        except Exception as exc:  # noqa: BLE001
            # Persistence failure must not corrupt the already-streamed answer.
            logger.warning("session_chat_persist_assistant_failed", error=str(exc))


# ---------------------------------------------------------------------------
# pure helpers
# ---------------------------------------------------------------------------
def _augment(question: str, attached: list[AttachedContext]) -> str:
    """Prepend the attached files as explicit grounding context.

    Mirrors the stateless client behaviour ("Regarding `path`: ...") so the
    model receives consistent prompts whether or not sessions are used.
    """
    if not attached:
        return question
    paths = ", ".join(f"`{a.path}`" for a in attached)
    return f"Regarding {paths}:\n\n{question}"


def _augment_stored(content: str, attached_context: Any) -> str:
    if not attached_context or not isinstance(attached_context, list):
        return content
    paths = ", ".join(
        f"`{item['path']}`"
        for item in attached_context
        if isinstance(item, dict) and item.get("path")
    )
    return f"Regarding {paths}:\n\n{content}" if paths else content


def _to_api_history(messages: list[ChatMessage]) -> list[ApiChatMessage]:
    """Rebuild the engine-facing history, re-augmenting user turns so the
    model sees the same context it originally answered against.
    """
    history: list[ApiChatMessage] = []
    for m in messages:
        if m.role == "user":
            history.append(
                ApiChatMessage(
                    role="user", content=_augment_stored(m.content, m.attached_context)
                )
            )
        elif m.role == "assistant":
            history.append(ApiChatMessage(role="assistant", content=m.content))
    return history


def _derive_title(question: str) -> str:
    title = " ".join(question.strip().split())
    if len(title) > _TITLE_MAX:
        title = title[: _TITLE_MAX - 1].rstrip() + "\u2026"
    return title or _DEFAULT_TITLE


def _safe_json(data: str) -> dict[str, Any] | None:
    try:
        parsed = json.loads(data)
    except (ValueError, TypeError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _error_event(message: str) -> dict[str, str]:
    from app.schemas.ai import ChatTokenEvent  # noqa: PLC0415

    return {
        "event": "error",
        "data": ChatTokenEvent(event="error", error=message).model_dump_json(),
    }


def _done_event() -> dict[str, str]:
    from app.schemas.ai import ChatTokenEvent  # noqa: PLC0415

    return {
        "event": "done",
        "data": ChatTokenEvent(event="done").model_dump_json(),
    }
