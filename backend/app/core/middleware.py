"""HTTP middleware — request IDs, timing, in-memory rate limiting."""
from __future__ import annotations

import time
import uuid
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings

logger = structlog.get_logger(__name__)


REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a request_id to every request and bind it to structlog context."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        rid = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        request.state.request_id = rid

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=rid,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception("request_failed", duration_ms=round(duration_ms, 2))
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[REQUEST_ID_HEADER] = rid
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple sliding-window in-memory rate limit per remote IP.

    Production deployments should swap this for a Redis-backed limiter or push
    the concern to the edge (Nginx / Cloudflare). This is sufficient for v1.

    The real client IP is read from the ``X-Real-IP`` / ``X-Forwarded-For``
    headers our own reverse proxy sets, falling back to the socket peer. Without
    this, every request behind the proxy shares the proxy's IP — so one abusive
    client would rate-limit *everyone*, and per-user limiting would be impossible.
    """

    def __init__(self, app: Any, settings: Settings) -> None:
        super().__init__(app)
        self._max_per_minute = settings.api_rate_limit_per_minute
        self._window_seconds = 60.0
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        # Exempt internal endpoints from rate limits.
        self._exempt_prefixes = ("/healthz", "/readyz", "/metrics")
        self._last_sweep = time.monotonic()

    @staticmethod
    def _client_ip(request: Request) -> str:
        # Trust the proxy-set headers (nginx overwrites X-Real-IP and appends
        # the real peer to X-Forwarded-For, so the rightmost entry is the one
        # added by our proxy and cannot be spoofed by the client).
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                return parts[-1]
        return request.client.host if request.client else "unknown"

    def _sweep_expired(self, now: float) -> None:
        """Drop fully-expired buckets so the map can't grow without bound."""
        if now - self._last_sweep < self._window_seconds:
            return
        self._last_sweep = now
        stale = [
            ip
            for ip, bucket in self._hits.items()
            if not bucket or now - bucket[-1] > self._window_seconds
        ]
        for ip in stale:
            del self._hits[ip]

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if any(request.url.path.startswith(p) for p in self._exempt_prefixes):
            return await call_next(request)

        client = self._client_ip(request)
        now = time.monotonic()
        self._sweep_expired(now)
        bucket = self._hits[client]

        while bucket and now - bucket[0] > self._window_seconds:
            bucket.popleft()

        if len(bucket) >= self._max_per_minute:
            retry_after = int(self._window_seconds - (now - bucket[0])) + 1
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"Max {self._max_per_minute} requests per minute",
                },
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        return await call_next(request)
