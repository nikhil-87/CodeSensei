"""Prometheus metric primitives and FastAPI middleware."""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Single registry per process. Tests reset via CollectorRegistry override.
REGISTRY = CollectorRegistry(auto_describe=True)

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests by method, path template, and status.",
    labelnames=("method", "path", "status"),
    registry=REGISTRY,
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds.",
    labelnames=("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

analysis_jobs_enqueued_total = Counter(
    "analysis_jobs_enqueued_total",
    "Number of analysis jobs enqueued.",
    registry=REGISTRY,
)

ai_chat_requests_total = Counter(
    "ai_chat_requests_total",
    "Number of AI chat completions.",
    labelnames=("cache",),
    registry=REGISTRY,
)

build_info = Gauge(
    "app_build_info",
    "Build / version info as labels; value is always 1.",
    labelnames=("version", "env"),
    registry=REGISTRY,
)


def render_metrics() -> tuple[bytes, str]:
    """Return Prometheus-formatted metrics payload + content type."""
    return generate_latest(REGISTRY), CONTENT_TYPE_LATEST


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration = time.perf_counter() - start
            path = _path_template(request)
            http_request_duration_seconds.labels(request.method, path).observe(duration)
            http_requests_total.labels(request.method, path, "500").inc()
            raise

        duration = time.perf_counter() - start
        path = _path_template(request)
        http_request_duration_seconds.labels(request.method, path).observe(duration)
        http_requests_total.labels(
            request.method, path, str(response.status_code)
        ).inc()
        return response


def _path_template(request: Request) -> str:
    """Use the route template (e.g. /repos/{id}) rather than the literal path."""
    route = request.scope.get("route")
    if route is not None and hasattr(route, "path"):
        return str(route.path)
    return request.url.path
