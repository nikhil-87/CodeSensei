"""Tests for :func:`persist_repository_analysis`."""
from __future__ import annotations

from engine.results import (
    ArchitectureLayer,
    ArchitectureReport,
    DeadCodeFinding,
    DependencyEdge,
    FileAnalysis,
    FileMetrics,
    RepositoryAnalysis,
    Symbol,
)
from worker.app.persistence import persist_repository_analysis


def _file(
    path: str,
    *,
    language: str = "python",
    symbols: tuple[Symbol, ...] = (),
) -> FileAnalysis:
    return FileAnalysis(
        path=path,
        language=language,
        size_bytes=100,
        line_count=10,
        sha256="0" * 64,
        symbols=symbols,
        imports=(),
        metrics=FileMetrics(
            cyclomatic=3, cognitive=2, lines_of_code=10, function_count=1, class_count=0
        ),
        parser="python_ast",
    )


def _analysis() -> RepositoryAnalysis:
    a = _file(
        "src/a.py",
        symbols=(
            Symbol("foo", "function", 1, 5),
            Symbol("Bar", "class", 6, 10, qualified_name="a.Bar"),
        ),
    )
    b = _file("src/b.py", symbols=(Symbol("baz", "function", 1, 3),))
    return RepositoryAnalysis(
        files=(a, b),
        dependencies=(
            DependencyEdge(from_path="src/a.py", to_path="src/b.py", kind="import", line=1),
            DependencyEdge(  # duplicate must be deduped
                from_path="src/a.py", to_path="src/b.py", kind="import", line=1
            ),
        ),
        cycles=(),
        languages={"python": 2},
        total_lines=20,
        dead_code=(
            DeadCodeFinding(
                file_path="src/b.py",
                symbol_name="baz",
                kind="function",
                line_start=1,
                confidence=0.7,
                reason="no inbound calls",
            ),
        ),
        architecture=ArchitectureReport(
            layers=(
                ArchitectureLayer(name="services", file_paths=("src/a.py",)),
                ArchitectureLayer(name="repositories", file_paths=("src/b.py",)),
            ),
            violations=(),
            mermaid="graph TD",
        ),
    )


def test_persist_creates_files_symbols_metrics_and_edges(make_repo, db_session):
    repo = make_repo()

    counts = persist_repository_analysis(
        db_session, repository_id=repo.id, analysis=_analysis()
    )
    db_session.commit()

    assert counts == {"files": 2, "symbols": 3, "edges": 1, "dead_code": 1}

    from app.models.dependency import Dependency
    from app.models.metric import Metric
    from app.models.repository import Repository, RepositoryStatus
    from app.models.source_file import SourceFile
    from app.models.symbol import Symbol as OrmSymbol

    assert db_session.query(SourceFile).count() == 2
    assert db_session.query(OrmSymbol).count() == 3
    assert db_session.query(Metric).count() == 2
    assert db_session.query(Dependency).count() == 1  # deduped

    fresh_repo = db_session.get(Repository, repo.id)
    assert fresh_repo.status == RepositoryStatus.READY
    assert fresh_repo.file_count == 2
    assert fresh_repo.total_lines == 20
    assert fresh_repo.languages is not None
    assert "python:2" in fresh_repo.languages


def test_persist_stamps_provenance_and_versions(make_repo, db_session):
    repo = make_repo()

    persist_repository_analysis(
        db_session,
        repository_id=repo.id,
        analysis=_analysis(),
        commit_hash="a" * 40,
        embedding_model="huggingface:test-model",
    )
    db_session.commit()

    from shared.config.analysis_version import (
        ANALYSIS_VERSION,
        PIPELINE_VERSION,
        SCHEMA_VERSION,
    )

    from app.models.repository import Repository

    fresh_repo = db_session.get(Repository, repo.id)
    assert fresh_repo.commit_hash == "a" * 40
    assert fresh_repo.embedding_model == "huggingface:test-model"
    assert fresh_repo.analysis_version == ANALYSIS_VERSION
    assert fresh_repo.pipeline_version == PIPELINE_VERSION
    assert fresh_repo.schema_version == SCHEMA_VERSION


def test_persist_marks_dead_code_symbols(make_repo, db_session):
    repo = make_repo()
    persist_repository_analysis(db_session, repository_id=repo.id, analysis=_analysis())
    db_session.commit()

    from app.models.metric import Metric
    from app.models.source_file import SourceFile
    from app.models.symbol import Symbol as OrmSymbol

    sf = (
        db_session.query(SourceFile)
        .filter(SourceFile.path == "src/b.py")
        .one()
    )
    metric = db_session.query(Metric).filter(Metric.file_id == sf.id).one()
    assert float(metric.dead_code_score) == 0.7

    baz = (
        db_session.query(OrmSymbol).filter(OrmSymbol.file_id == sf.id, OrmSymbol.name == "baz").one()
    )
    assert baz.is_used is False


def test_persist_replaces_prior_results_idempotently(make_repo, db_session):
    repo = make_repo()

    persist_repository_analysis(db_session, repository_id=repo.id, analysis=_analysis())
    db_session.commit()
    persist_repository_analysis(db_session, repository_id=repo.id, analysis=_analysis())
    db_session.commit()

    from app.models.source_file import SourceFile

    # Still 2 files, not 4 — the previous run was wiped.
    assert db_session.query(SourceFile).count() == 2
