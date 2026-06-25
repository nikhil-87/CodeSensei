"""DeadCodeService — surfaces unreachable symbols persisted by the worker."""
from __future__ import annotations

import uuid
from collections import Counter

from app.cache.redis_cache import RedisCache
from app.core.exceptions import (
    AnalysisNotReadyError,
    RepositoryNotFoundError,
)
from app.models.repository import RepositoryStatus
from app.models.symbol import SymbolKind
from app.repositories.repository_repository import RepositoryRepository
from app.repositories.source_file_repository import SourceFileRepository
from app.repositories.symbol_repository import SymbolRepository
from app.schemas.dead_code import DeadCodeItem, DeadCodeReport


class DeadCodeService:
    def __init__(
        self,
        repository_repo: RepositoryRepository,
        file_repo: SourceFileRepository,
        symbol_repo: SymbolRepository,
        cache: RedisCache,
    ) -> None:
        self._repos = repository_repo
        self._files = file_repo
        self._symbols = symbol_repo
        self._cache = cache

    async def report(self, repository_id: uuid.UUID) -> DeadCodeReport:
        cache_key = f"repo:{repository_id}:dead_code"
        cached = await self._cache.get_json(cache_key)
        if cached is not None:
            return DeadCodeReport.model_validate(cached)

        repo = await self._repos.get(repository_id)
        if repo is None:
            raise RepositoryNotFoundError(f"Repository {repository_id} not found")
        if repo.status != RepositoryStatus.READY:
            raise AnalysisNotReadyError(
                f"Repository status is {repo.status.value}; analysis not ready"
            )

        unused = await self._symbols.list_unused_for_repository(repository_id)
        kind_totals: Counter[SymbolKind] = Counter()

        items: list[DeadCodeItem] = []
        for symbol, file in unused:
            kind_totals[symbol.kind] += 1
            items.append(
                DeadCodeItem(
                    file_id=file.id,
                    path=file.path,
                    symbol_name=symbol.name,
                    kind=symbol.kind,
                    line_start=symbol.line_start,
                    line_end=symbol.line_end,
                    confidence=_confidence(symbol.is_exported, symbol.usage_count),
                    reason=_reason(symbol.is_exported, symbol.usage_count),
                )
            )

        summary = {k.value: v for k, v in kind_totals.items()}
        summary["total"] = len(items)

        report = DeadCodeReport(
            repository_id=repository_id,
            items=items,
            summary=summary,
        )
        await self._cache.set_json(cache_key, report.model_dump(mode="json"))
        return report


def _confidence(is_exported: bool, usage_count: int) -> float:
    """Heuristic: exported symbols may be used externally; reduce confidence."""
    if usage_count > 0:
        return 0.0
    return 0.6 if is_exported else 0.95


def _reason(is_exported: bool, usage_count: int) -> str:
    if usage_count > 0:
        return "Has internal usages but may still be unreachable"
    return (
        "Exported but no internal callers — verify external API consumers"
        if is_exported
        else "No incoming references found"
    )
