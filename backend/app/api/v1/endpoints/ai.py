"""AI chat endpoint — token-streamed SSE.

The real RAG implementation lives in the analysis-engine
(``engine/ai/*``) and is wired through :class:`AIService`. The endpoint
contract — request validation, SSE event names, error framing — is
final. AI infra outages produce a single ``error`` SSE event followed
by a ``done`` event so the client always sees a clean terminator.
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import structlog
from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.core.dependencies import AIServiceDep, OptionalUserDep, RepositoryServiceDep
from app.observability.metrics import ai_chat_requests_total
from app.schemas.ai import ChatRequest, ChatTokenEvent

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post(
    "/chat",
    summary="Stream an AI answer about the repository (SSE)",
)
async def chat(
    payload: ChatRequest,
    ai_service: AIServiceDep,
    repo_service: RepositoryServiceDep,
    user: OptionalUserDep,
) -> EventSourceResponse:
    # Authorize against the target repo first: owners or public repos only.
    # Raises 404 if the caller may not see it (same IDOR-safe behaviour as
    # the read endpoints).
    await repo_service.get_for_user(
        payload.repository_id, user_id=user.id if user else None
    )
    ai_chat_requests_total.labels("served").inc()

    async def stream() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in ai_service.stream_chat(payload):
                yield event
        except Exception:  # noqa: BLE001 — defence in depth
            # Never surface the raw exception text to the client — it can leak
            # internal details (hostnames, stack context). Log it server-side.
            logger.exception("ai_chat_stream_failed")
            error = ChatTokenEvent(
                event="error",
                error="The assistant ran into a problem. Please try again.",
            )
            yield {"event": "error", "data": error.model_dump_json()}
            done = ChatTokenEvent(event="done")
            yield {"event": "done", "data": done.model_dump_json()}

    return EventSourceResponse(stream())
