"""ImpactService — reverse-dependency walk with risk scoring."""
from __future__ import annotations

import math
import uuid
from collections import defaultdict, deque

from app.core.exceptions import (
    AnalysisNotReadyError,
    RepositoryNotFoundError,
    SourceFileNotFoundError,
)
from app.models.repository import RepositoryStatus
from app.repositories.dependency_repository import DependencyRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.source_file_repository import SourceFileRepository
from app.schemas.impact import (
    ImpactAnalysisRequest,
    ImpactAnalysisResponse,
    ImpactedFile,
)


class ImpactService:
    def __init__(
        self,
        repository_repo: RepositoryRepository,
        file_repo: SourceFileRepository,
        dep_repo: DependencyRepository,
    ) -> None:
        self._repos = repository_repo
        self._files = file_repo
        self._deps = dep_repo

    async def analyze(
        self,
        repository_id: uuid.UUID,
        payload: ImpactAnalysisRequest,
    ) -> ImpactAnalysisResponse:
        repo = await self._repos.get(repository_id)
        if repo is None:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")
        if repo.status != RepositoryStatus.READY:
            raise AnalysisNotReadyError(
                f"Repository status is {repo.status.value}; analysis not ready"
            )

        source = await self._files.get_by_path(repository_id, payload.file_path)
        if source is None:
            raise SourceFileNotFoundError(
                f"File {payload.file_path!r} not found in repository"
            )

        edges = await self._deps.list_for_repository(repository_id)
        reverse_adj: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)
        for e in edges:
            reverse_adj[e.to_file_id].append(e.from_file_id)

        # BFS upstream from `source`, limited by max_depth.
        distances: dict[uuid.UUID, int] = {source.id: 0}
        queue: deque[uuid.UUID] = deque([source.id])
        while queue:
            current = queue.popleft()
            depth = distances[current]
            if depth >= payload.max_depth:
                continue
            for parent in reverse_adj.get(current, ()):
                if parent in distances:
                    continue
                distances[parent] = depth + 1
                queue.append(parent)

        # Drop the source itself; rank the rest.
        distances.pop(source.id, None)
        path_lookup = {
            f.id: f.path
            for f in await self._files.list_for_repository(repository_id, limit=10_000)
        }

        impacted = [
            ImpactedFile(
                file_id=fid,
                path=path_lookup.get(fid, "<unknown>"),
                distance=dist,
                risk_score=_risk(dist, payload.max_depth),
            )
            for fid, dist in distances.items()
        ]
        impacted.sort(key=lambda i: (i.distance, -i.risk_score, i.path))

        overall_risk = _aggregate_risk(impacted)

        return ImpactAnalysisResponse(
            repository_id=repository_id,
            source_file=source.path,
            impacted_files=impacted,
            risk_score=overall_risk,
            summary=_summarize(source.path, impacted, overall_risk),
        )


def _risk(distance: int, max_depth: int) -> float:
    # Closer dependents are higher risk; exponential decay.
    return round(math.exp(-0.5 * (distance - 1)), 3) if distance > 0 else 1.0


def _aggregate_risk(impacted: list[ImpactedFile]) -> float:
    if not impacted:
        return 0.0
    score = sum(i.risk_score for i in impacted)
    # Squash into 0..1 via sigmoid so 50+ impacted files saturate to ~1.
    return round(1.0 - math.exp(-score / 8), 3)


def _summarize(
    source: str,
    impacted: list[ImpactedFile],
    risk: float,
) -> str:
    if not impacted:
        return f"Changing {source} has no reverse dependents within the analyzed depth."
    direct = sum(1 for i in impacted if i.distance == 1)
    return (
        f"Changing {source} may affect {len(impacted)} files "
        f"({direct} direct dependents). Overall risk: {risk:.2f}."
    )
