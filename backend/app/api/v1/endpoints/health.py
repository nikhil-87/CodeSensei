"""Health & readiness endpoints + Prometheus metrics exposition."""
from __future__ import annotations

from fastapi import APIRouter, Response, status

from app import __version__
from app.cache.redis_cache import get_redis_cache
from app.core.config import get_settings
from app.db.session import get_engine
from app.observability.metrics import render_metrics
from app.schemas.common import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def healthz() -> HealthResponse:
    """Liveness — process is up. Never fails unless the process is dying."""
    return HealthResponse(status="ok", version=__version__)


@router.get("/readyz", response_model=HealthResponse)
async def readyz() -> HealthResponse:
    """Readiness — every downstream we need is reachable."""
    settings = get_settings()
    checks: dict[str, str] = {}

    # Postgres
    try:
        engine = get_engine(settings)
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        checks["postgres"] = "ok"
    except Exception as exc:  # noqa: BLE001
        checks["postgres"] = f"error: {exc.__class__.__name__}"

    # Redis (cache)
    try:
        cache = get_redis_cache(settings)
        checks["redis"] = "ok" if await cache.ping() else "unreachable"
    except Exception as exc:  # noqa: BLE001
        checks["redis"] = f"error: {exc.__class__.__name__}"

    overall = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return HealthResponse(status=overall, version=__version__, checks=checks)


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    payload, content_type = render_metrics()
    return Response(content=payload, media_type=content_type)
