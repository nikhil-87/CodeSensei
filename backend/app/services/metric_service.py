"""MetricService — complexity rankings + repository-level summary."""
from __future__ import annotations

import uuid

from app.cache.redis_cache import RedisCache
from app.core.exceptions import (
    AnalysisNotReadyError,
    RepositoryNotFoundError,
)
from app.models.repository import RepositoryStatus
from app.repositories.metric_repository import MetricRepository
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.source_file_repository import SourceFileRepository
from app.schemas.metric import ComplexityRanking, FileComplexity


class MetricService:
    def __init__(
        self,
        repository_repo: RepositoryRepository,
        file_repo: SourceFileRepository,
        metric_repo: MetricRepository,
        cache: RedisCache,
    ) -> None:
        self._repos = repository_repo
        self._files = file_repo
        self._metrics = metric_repo
        self._cache = cache

    async def complexity_ranking(
        self,
        repository_id: uuid.UUID,
        *,
        top_n: int = 10,
    ) -> ComplexityRanking:
        cache_key = f"repo:{repository_id}:complexity:{top_n}"
        cached = await self._cache.get_json(cache_key)
        if cached is not None:
            return ComplexityRanking.model_validate(cached)

        repo = await self._repos.get(repository_id)
        if repo is None:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")
        if repo.status != RepositoryStatus.READY:
            raise AnalysisNotReadyError(
                f"Repository status is {repo.status.value}; analysis not ready"
            )

        top_pairs = await self._metrics.top_complex(repository_id, limit=top_n)
        averages = await self._metrics.averages(repository_id)

        ranking = ComplexityRanking(
            repository_id=repository_id,
            top_files=[
                FileComplexity(
                    file_id=metric.file_id,
                    path=file.path,
                    language=file.language,
                    cyclomatic=metric.cyclomatic,
                    cognitive=metric.cognitive,
                    lines_of_code=metric.lines_of_code,
                    function_count=metric.function_count,
                    class_count=metric.class_count,
                )
                for metric, file in top_pairs
            ],
            average_cyclomatic=averages["cyclomatic"],
            average_cognitive=averages["cognitive"],
            median_lines_of_code=averages["loc_median"],
        )
        await self._cache.set_json(cache_key, ranking.model_dump(mode="json"))
        return ranking
