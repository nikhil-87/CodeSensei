"""DependencyService — graph queries served from persisted data."""
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
from app.schemas.dependency import (
    DependencyEdge,
    DependencyGraphResponse,
    GraphNode,
)


class DependencyService:
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

    async def get_graph(self, repository_id: uuid.UUID) -> DependencyGraphResponse:
        cache_key = f"repo:{repository_id}:graph"
        cached = await self._cache.get_json(cache_key)
        if cached is not None:
            return DependencyGraphResponse.model_validate(cached)

        repo = await self._repos.get(repository_id)
        if repo is None:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")
        if repo.status != RepositoryStatus.READY:
            raise AnalysisNotReadyError(
                f"Repository status is {repo.status.value}; analysis not ready"
            )

        files = await self._files.list_for_repository(repository_id, limit=10_000)
        edges = await self._deps.list_for_repository(repository_id)

        in_deg: dict[uuid.UUID, int] = defaultdict(int)
        out_deg: dict[uuid.UUID, int] = defaultdict(int)
        for e in edges:
            out_deg[e.from_file_id] += 1
            in_deg[e.to_file_id] += 1

        nodes = [
            GraphNode(
                id=f.id,
                path=f.path,
                language=f.language,
                line_count=f.line_count,
                in_degree=in_deg[f.id],
                out_degree=out_deg[f.id],
            )
            for f in files
        ]

        graph_edges = [
            DependencyEdge(
                **{
                    "from": e.from_file_id,
                    "to": e.to_file_id,
                    "kind": e.kind,
                    "symbol": e.symbol,
                }
            )
            for e in edges
        ]

        cycles = self._detect_cycles(nodes, graph_edges)

        response = DependencyGraphResponse(
            repository_id=repository_id,
            nodes=nodes,
            edges=graph_edges,
            cycles=cycles,
        )
        await self._cache.set_json(cache_key, response.model_dump(mode="json"))
        return response

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _detect_cycles(
        nodes: list[GraphNode],
        edges: list[DependencyEdge],
    ) -> list[list[uuid.UUID]]:
        """Tarjan's SCC. Returns SCCs with more than one node (or self-loops)."""
        index: dict[uuid.UUID, int] = {}
        lowlink: dict[uuid.UUID, int] = {}
        stack: list[uuid.UUID] = []
        on_stack: set[uuid.UUID] = set()
        sccs: list[list[uuid.UUID]] = []
        counter = [0]

        adj: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
        for e in edges:
            adj[e.from_id].append(e.to_id)

        def strong_connect(v: uuid.UUID) -> None:
            index[v] = lowlink[v] = counter[0]
            counter[0] += 1
            stack.append(v)
            on_stack.add(v)
            for w in adj.get(v, ()):
                if w not in index:
                    strong_connect(w)
                    lowlink[v] = min(lowlink[v], lowlink[w])
                elif w in on_stack:
                    lowlink[v] = min(lowlink[v], index[w])
            if lowlink[v] == index[v]:
                component: list[uuid.UUID] = []
                while True:
                    w = stack.pop()
                    on_stack.discard(w)
                    component.append(w)
                    if w == v:
                        break
                # Self-loop or multi-node SCC = a cycle.
                if len(component) > 1 or v in adj.get(v, ()):
                    sccs.append(component)

        for n in nodes:
            if n.id not in index:
                strong_connect(n.id)

        return sccs
