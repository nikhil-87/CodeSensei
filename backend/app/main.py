"""FastAPI application factory + lifespan.

Run with: `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
"""
from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app import __version__
from app.api.v1.endpoints import health as health_endpoints
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import DomainError
from app.core.logging import configure_logging
from app.core.middleware import RateLimitMiddleware, RequestContextMiddleware
from app.db.session import dispose_engine, get_engine
from app.observability.metrics import PrometheusMiddleware, build_info

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    configure_logging(settings)
    build_info.labels(version=__version__, env=settings.app_env).set(1)
    logger.info(
        "app_starting",
        version=__version__,
        env=settings.app_env,
        log_level=settings.app_log_level,
    )

    # Safeguard: mock auth must never run in production. The setting is ignored
    # there (see Settings.mock_auth_enabled); surface a loud error if someone
    # still set it, and warn clearly when it IS active in dev/test.
    if settings.mock_auth and settings.is_production:
        logger.error(
            "mock_auth_ignored_in_production",
            detail="MOCK_AUTH=true was set but is ignored because APP_ENV=production",
        )
    elif settings.mock_auth_enabled:
        logger.warning(
            "mock_auth_enabled",
            detail="Authentication is mocked — every request is the predefined mock user",
            username=settings.mock_auth_username,
            env=settings.app_env,
        )

    # Fail fast if the selected AI providers are missing required credentials.
    from shared.config.providers import validate_provider_config

    provider_errors = validate_provider_config(
        llm_provider=settings.llm_provider,
        embedding_provider=settings.embedding_provider,
        groq_api_key=settings.groq_api_key,
        huggingface_api_key=settings.huggingface_api_key,
    )
    if provider_errors:
        for err in provider_errors:
            logger.error("invalid_provider_config", error=err)
        raise RuntimeError("; ".join(provider_errors))

    # Warm the DB engine pool (best-effort — readiness probe is the contract).
    try:
        engine = get_engine(settings)
        async with engine.connect() as conn:
            await conn.exec_driver_sql("SELECT 1")
        logger.info("postgres_reachable")
    except Exception as exc:  # noqa: BLE001
        logger.warning("postgres_unreachable_on_start", error=str(exc))

    # Start the stuck-job reaper so a crashed worker can never leave a
    # repository permanently stuck in RUNNING (the active-job unique index
    # would otherwise block all re-analysis).
    reaper_task: asyncio.Task[None] | None = None
    if settings.analysis_reaper_enabled:
        from app.services.analysis_reaper import run_reaper_loop

        reaper_task = asyncio.create_task(run_reaper_loop(settings))

    yield

    if reaper_task is not None:
        reaper_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await reaper_task

    await dispose_engine(settings)
    logger.info("app_stopped")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    # Hide interactive API docs + the OpenAPI schema in production: they map the
    # entire attack surface for free and aren't needed by end users.
    docs_enabled = not settings.is_production

    app = FastAPI(
        title="CodeSensei API",
        description=(
            "REST + SSE API for intelligent code analysis: parsing, "
            "graphs, metrics, dead-code, impact, architecture, documentation, "
            "and AI Q&A."
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )

    # Middleware order matters: outermost first.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    app.add_middleware(PrometheusMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(RateLimitMiddleware, settings=settings)

    # Routes
    app.include_router(api_router, prefix="/api/v1")
    # Mount health endpoints unprefixed too — friendlier for probes/proxies.
    app.include_router(health_endpoints.router)

    _install_exception_handlers(app)
    return app


def _install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain_handler(_: Request, exc: DomainError) -> JSONResponse:
        logger.warning(
            "domain_error",
            error_code=exc.error_code,
            message=exc.message,
            **exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": "Request payload failed validation",
                "details": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled_exception", error_type=exc.__class__.__name__)
        return JSONResponse(
            status_code=500,
            content={
                "error": "internal_error",
                "message": "An unexpected error occurred",
            },
        )


# Top-level app instance — picked up by uvicorn.
app = create_app()
