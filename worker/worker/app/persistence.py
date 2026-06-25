"""Translate :class:`engine.RepositoryAnalysis` into ORM rows.

Replaces the *previous* analysis run for the same repository — we delete
``SourceFile`` rows (cascade removes Symbols, Metrics, Dependencies) and
re-insert. This is acceptable because the analysis is *the* source of
truth and a re-run typically follows a code change; users always want a
clean view.
"""
from __future__ import annotations

import uuid
from collections import Counter
from collections.abc import Iterable
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import structlog
from sqlalchemy import delete

from engine.results import (
    DependencyEdge,
    FileAnalysis,
    RepositoryAnalysis,
    Symbol as EngineSymbol,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)


# Engine-side symbol kind strings → ORM enum values (already aligned).
_KIND_MAP: dict[str, str] = {
    "function": "function",
    "method": "method",
    "class": "class",
    "interface": "interface",
    "struct": "struct",
    "enum": "enum",
    "variable": "variable",
    "constant": "constant",
    "type_alias": "type_alias",
    "module": "module",
}

# Engine-side dependency kinds.
_DEP_KIND_MAP: dict[str, str] = {
    "import": "import",
    "inheritance": "inheritance",
    "call": "call",
    "instantiation": "instantiation",
    "reference": "reference",
}


def persist_repository_analysis(
    session: "Session",
    *,
    repository_id: uuid.UUID,
    analysis: RepositoryAnalysis,
    commit_hash: str | None = None,
    embedding_model: str | None = None,
) -> dict[str, int]:
    """Persist ``analysis`` into the DB under ``repository_id``.

    ``commit_hash`` and ``embedding_model`` stamp the result's provenance so a
    later read can tell whether it was produced by the current pipeline. The
    analysis/pipeline/schema version stamps are sourced from
    :mod:`shared.config.analysis_version` — the single source of truth.

    Returns a small counters dict for logging / metrics.
    """
    # Late imports — keeps the worker package importable without the
    # backend on PYTHONPATH (e.g. linting only the worker).
    from shared.config.analysis_version import (  # noqa: PLC0415
        ANALYSIS_VERSION,
        PIPELINE_VERSION,
        SCHEMA_VERSION,
    )

    from app.models.dependency import Dependency, DependencyKind  # noqa: PLC0415
    from app.models.metric import Metric  # noqa: PLC0415
    from app.models.repository import Repository, RepositoryStatus  # noqa: PLC0415
    from app.models.source_file import SourceFile  # noqa: PLC0415
    from app.models.symbol import Symbol, SymbolKind  # noqa: PLC0415

    repo = session.get(Repository, repository_id)
    if repo is None:
        raise ValueError(f"Repository {repository_id} not found")

    # 1. Wipe the prior result so we never present stale rows.
    session.execute(
        delete(SourceFile).where(SourceFile.repository_id == repository_id)
    )
    session.flush()

    # 2. Insert SourceFile rows; remember a (path → SourceFile) map for
    #    edge resolution.
    path_to_file: dict[str, SourceFile] = {}
    for file in analysis.files:
        sf = SourceFile(
            repository_id=repository_id,
            path=file.path,
            language=file.language or "unknown",
            line_count=file.line_count,
            size_bytes=file.size_bytes,
            sha256=file.sha256,
        )
        session.add(sf)
        path_to_file[file.path] = sf
    session.flush()  # populate sf.id

    # 3. Per-file Metric + Symbols.
    path_to_metric: dict[str, Metric] = {}
    path_to_symbols: dict[str, list[Symbol]] = {}
    for file in analysis.files:
        sf = path_to_file[file.path]
        metric = Metric(
            file_id=sf.id,
            cyclomatic=file.metrics.cyclomatic,
            cognitive=file.metrics.cognitive,
            lines_of_code=file.metrics.lines_of_code,
            function_count=file.metrics.function_count,
            class_count=file.metrics.class_count,
            dead_code_score=0.0,
        )
        session.add(metric)
        path_to_metric[file.path] = metric
        symbols: list[Symbol] = []
        for sym in file.symbols:
            orm_sym = _to_orm_symbol(Symbol, SymbolKind, sf.id, sym)
            session.add(orm_sym)
            symbols.append(orm_sym)
        path_to_symbols[file.path] = symbols

    # 4. Apply dead-code findings via our own maps (don't rely on
    #    relationship lazy-loading mid-flush).
    for finding in analysis.dead_code:
        metric = path_to_metric.get(finding.file_path)
        if metric is not None:
            metric.dead_code_score = max(
                float(metric.dead_code_score), float(finding.confidence)
            )
        for orm_sym in path_to_symbols.get(finding.file_path, []):
            if orm_sym.name == finding.symbol_name:
                orm_sym.is_used = False
    session.flush()

    # 5. Resolved dependency edges.
    edge_count = 0
    for edge in _unique_edges(analysis.dependencies):
        from_sf = path_to_file.get(edge.from_path)
        to_sf = path_to_file.get(edge.to_path)
        if from_sf is None or to_sf is None:
            continue
        kind_value = _DEP_KIND_MAP.get(edge.kind, "reference")
        session.add(
            Dependency(
                from_file_id=from_sf.id,
                to_file_id=to_sf.id,
                kind=DependencyKind(kind_value),
                symbol=edge.symbol,
                line=edge.line,
            )
        )
        edge_count += 1

    # 6. Aggregate stats on the Repository row.
    languages = Counter(
        f.language or "unknown" for f in analysis.files
    )
    top = ",".join(f"{k}:{v}" for k, v in languages.most_common(10))
    repo.file_count = analysis.file_count
    repo.total_lines = sum(f.line_count for f in analysis.files)
    repo.languages = top[:512] or None
    repo.status = RepositoryStatus.READY
    repo.error_message = None
    repo.analyzed_at = datetime.now(UTC)
    # Provenance + version stamps so a later read can detect a stale analysis.
    repo.commit_hash = commit_hash
    repo.embedding_model = embedding_model
    repo.analysis_version = ANALYSIS_VERSION
    repo.pipeline_version = PIPELINE_VERSION
    repo.schema_version = SCHEMA_VERSION

    session.flush()

    counts = {
        "files": len(analysis.files),
        "symbols": sum(len(f.symbols) for f in analysis.files),
        "edges": edge_count,
        "dead_code": len(analysis.dead_code),
    }
    logger.info("persisted_analysis", repository_id=str(repository_id), **counts)
    return counts


# ---------------------------------------------------------------------------
def _to_orm_symbol(SymbolModel, SymbolKind, file_id, sym: EngineSymbol):  # type: ignore[no-untyped-def]
    kind_value = _KIND_MAP.get(sym.kind, "function")
    return SymbolModel(
        file_id=file_id,
        name=sym.name[:512],
        qualified_name=sym.qualified_name[:1024] if sym.qualified_name else None,
        kind=SymbolKind(kind_value),
        line_start=sym.line_start,
        line_end=sym.line_end,
        is_exported=sym.is_exported,
        is_used=True,
        usage_count=0,
    )


def _unique_edges(edges: Iterable[DependencyEdge]) -> Iterable[DependencyEdge]:
    """Drop edge duplicates that would violate ``uq_dependencies_edge``."""
    seen: set[tuple[str, str, str, str | None]] = set()
    for e in edges:
        key = (e.from_path, e.to_path, e.kind, e.symbol)
        if key in seen:
            continue
        seen.add(key)
        yield e
