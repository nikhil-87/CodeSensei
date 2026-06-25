"""Architecture classifier — layer detection + violation reporting."""
from __future__ import annotations

from engine.architecture.classifier import classify_architecture
from engine.results import (
    DependencyEdge,
    FileAnalysis,
    FileMetrics,
)


def _file(path: str) -> FileAnalysis:
    return FileAnalysis(
        path=path,
        language="python",
        size_bytes=0,
        line_count=0,
        sha256="",
        symbols=(),
        imports=(),
        metrics=FileMetrics(0, 0, 0, 0, 0),
        parser="test",
    )


def test_classifies_known_layers() -> None:
    files = [
        _file("api/users.py"),
        _file("services/user_service.py"),
        _file("repositories/user_repo.py"),
        _file("models/user.py"),
        _file("infrastructure/db.py"),
        _file("tests/test_users.py"),
        _file("tools/random.py"),  # unclassified -> "other"
    ]
    report = classify_architecture(files, [])
    layer_names = {layer.name for layer in report.layers}
    assert {
        "controllers",
        "services",
        "repositories",
        "models",
        "infrastructure",
        "tests",
        "other",
    } <= layer_names


def test_flags_layering_violation() -> None:
    files = [_file("api/users.py"), _file("models/user.py")]
    edges = [
        # models depending on api is a violation (lower layer importing higher)
        DependencyEdge(from_path="models/user.py", to_path="api/users.py", kind="import"),
    ]
    report = classify_architecture(files, edges)
    assert report.violations
    assert any("models" in v and "controllers" in v for v in report.violations)


def test_no_violation_for_inward_dependency() -> None:
    files = [_file("api/users.py"), _file("services/user_service.py")]
    edges = [
        DependencyEdge(
            from_path="api/users.py",
            to_path="services/user_service.py",
            kind="import",
        ),
    ]
    report = classify_architecture(files, edges)
    assert not report.violations


def test_mermaid_renders_layer_nodes() -> None:
    files = [_file("api/x.py"), _file("services/y.py")]
    report = classify_architecture(files, [])
    assert "flowchart TB" in report.mermaid
    assert "controllers" in report.mermaid
    assert "services" in report.mermaid
