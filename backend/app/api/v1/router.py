"""v1 router aggregator."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    analysis,
    architecture,
    auth,
    chat_sessions,
    complexity,
    dead_code,
    dependencies,
    discover,
    documentation,
    health,
    impact,
    repositories,
    stars,
    users,
)

api_router = APIRouter()

# Health endpoints are mounted at root in main.py for K8s probe ergonomics,
# but we also expose them under /api/v1 for symmetry.
api_router.include_router(health.router)

api_router.include_router(auth.router)
api_router.include_router(repositories.router)
api_router.include_router(stars.router)
api_router.include_router(discover.router)
api_router.include_router(users.router)
api_router.include_router(analysis.router)
api_router.include_router(dependencies.router)
api_router.include_router(dead_code.router)
api_router.include_router(complexity.router)
api_router.include_router(impact.router)
api_router.include_router(architecture.router)
api_router.include_router(documentation.router)
api_router.include_router(ai.router)
api_router.include_router(chat_sessions.router)
