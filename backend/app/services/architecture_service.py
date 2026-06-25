"""ArchitectureService — derives layers/components/diagrams from persisted data.

The richer architecture algorithms (Louvain community detection, layer
heuristics) live in `analysis-engine` and run inside the worker. This service
serves a cached representation; if no engine-produced summary is cached it
falls back to a path-prefix based heuristic so the endpoint is always useful.
"""
from __future__ import annotations

import uuid
from collections import defaultdict

from app.cache.redis_cache import RedisCache
from app.core.exceptions import (
    AnalysisNotReadyError,
    RepositoryNotFoundError,
)
from app.models.repository import RepositoryStatus
from app.repositories.dependency_repository import DependencyRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.source_file_repository import SourceFileRepository
from app.schemas.architecture import ArchitectureReport, LayerInfo

_LAYER_HINTS = (
    ("controllers", ("api", "controller", "endpoint", "route", "handler")),
    ("services", ("service",)),
    ("repositories", ("repository", "repositories", "dao", "store")),
    ("models", ("model", "schema", "entity", "domain")),
    ("infrastructure", ("infra", "config", "settings", "db", "cache")),
    ("ui", ("ui", "frontend", "view", "component", "page")),
    ("tests", ("test", "spec")),
)


class ArchitectureService:
    def __init__(
        self,
        repository_repo: RepositoryRepository,
        file_repo: SourceFileRepository,
        dep_repo: DependencyRepository,
        cache: RedisCache,
    ) -> None:
        self._repos = repository_repo
        self._files = file_repo
        self._deps = dep_repo
        self._cache = cache

    async def report(self, repository_id: uuid.UUID) -> ArchitectureReport:
        cache_key = f"repo:{repository_id}:architecture"
        cached = await self._cache.get_json(cache_key)
        if cached is not None:
            return ArchitectureReport.model_validate(cached)

        repo = await self._repos.get(repository_id)
        if repo is None:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")
        if repo.status != RepositoryStatus.READY:
            raise AnalysisNotReadyError(
                f"Repository status is {repo.status.value}; analysis not ready"
            )

        files = await self._files.list_for_repository(repository_id, limit=10_000)

        # Layers from path-prefix heuristic.
        layer_buckets: dict[str, list[str]] = defaultdict(list)
        for f in files:
            layer_buckets[_classify_layer(f.path)].append(f.path)

        layers = [
            LayerInfo(name=name, file_count=len(paths), files=sorted(paths)[:20])
            for name, paths in sorted(
                layer_buckets.items(), key=lambda kv: -len(kv[1])
            )
        ]

        # Components from top-level path prefix.
        component_buckets: dict[str, list[str]] = defaultdict(list)
        for f in files:
            top = f.path.split("/", 1)[0] if "/" in f.path else "."
            component_buckets[top].append(f.path)
        components = [
            LayerInfo(name=name, file_count=len(paths), files=sorted(paths)[:20])
            for name, paths in sorted(
                component_buckets.items(), key=lambda kv: -len(kv[1])
            )[:15]
        ]

        mermaid = _render_mermaid(layers)
        summary = (
            f"Repository has {len(files)} files across {len(layers)} discoverable "
            f"layers and {len(components)} top-level components."
        )

        report = ArchitectureReport(
            repository_id=repository_id,
            layers=layers,
            components=components,
            mermaid_diagram=mermaid,
            summary=summary,
        )
        await self._cache.set_json(cache_key, report.model_dump(mode="json"))
        return report


def _classify_layer(path: str) -> str:
    lowered = path.lower()
    for layer_name, hints in _LAYER_HINTS:
        if any(h in lowered for h in hints):
            return layer_name
    return "other"


def _render_mermaid(layers: list[LayerInfo]) -> str:
    if not layers:
        return "flowchart TB\n    empty[No layers detected]"
    lines = ["flowchart TB"]
    for layer in layers:
        safe = layer.name.replace(" ", "_")
        lines.append(f'    {safe}["{layer.name}<br/>({layer.file_count} files)"]')
    # Connect each layer to the one below for visual readability.
    for prev, curr in zip(layers, layers[1:], strict=False):
        lines.append(
            f"    {prev.name.replace(' ', '_')} --> {curr.name.replace(' ', '_')}"
        )
    return "\n".join(lines)
