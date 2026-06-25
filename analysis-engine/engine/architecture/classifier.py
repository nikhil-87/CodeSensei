"""Heuristic layer / architecture discovery.

Walks the file paths + dependency edges and classifies each file into a
named layer. Detects layering violations — an edge from a "lower" layer
to a "higher" one (e.g. ``models`` importing ``api``) is reported.

This is a pragmatic substitute for source-of-truth ADRs; it's enough to
power the architecture diagram on the dashboard.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from engine.results import (
    ArchitectureLayer,
    ArchitectureReport,
    DependencyEdge,
    FileAnalysis,
)


# Order matters: index 0 is "outermost" (most dependent), index -1 is
# "innermost" (most depended-upon). Imports MUST flow from outer → inner.
_LAYER_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("ui", ("frontend/", "ui/", "web/", "client/", "src/components/", "src/pages/")),
    ("controllers", ("controllers/", "api/", "endpoints/", "routes/", "handlers/")),
    ("services", ("services/", "use_cases/", "domain/services/", "application/")),
    ("repositories", ("repositories/", "data/", "dao/", "persistence/")),
    ("models", ("models/", "entities/", "domain/", "schemas/")),
    ("infrastructure", ("infrastructure/", "infra/", "adapters/", "platform/")),
    ("tests", ("tests/", "test/", "__tests__/")),
)
_LAYER_INDEX: dict[str, int] = {name: i for i, (name, _) in enumerate(_LAYER_RULES)}


def classify_architecture(
    files: Iterable[FileAnalysis],
    edges: Iterable[DependencyEdge],
) -> ArchitectureReport:
    """Group files into layers + flag layering violations + emit Mermaid."""
    files_tuple = tuple(files)

    layer_to_paths: dict[str, list[str]] = defaultdict(list)
    layer_for: dict[str, str] = {}
    for f in files_tuple:
        layer = _classify_file(f.path)
        if layer is None:
            layer = "other"
        layer_to_paths[layer].append(f.path)
        layer_for[f.path] = layer

    violations: list[str] = []
    cross_layer_edges: dict[tuple[str, str], int] = defaultdict(int)
    for edge in edges:
        from_layer = layer_for.get(edge.from_path)
        to_layer = layer_for.get(edge.to_path)
        if not from_layer or not to_layer or from_layer == to_layer:
            continue
        cross_layer_edges[(from_layer, to_layer)] += 1
        if _violates(from_layer, to_layer):
            violations.append(
                f"{from_layer} → {to_layer}: {edge.from_path} imports "
                f"{edge.to_path} (lower-to-higher layer call)"
            )

    layers_sorted = sorted(
        layer_to_paths.items(), key=lambda kv: _LAYER_INDEX.get(kv[0], 99)
    )
    layers = tuple(
        ArchitectureLayer(name=name, file_paths=tuple(paths))
        for name, paths in layers_sorted
    )

    return ArchitectureReport(
        layers=layers,
        violations=tuple(violations[:50]),  # keep payload bounded
        mermaid=_render_mermaid(layers, cross_layer_edges),
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _classify_file(path: str) -> str | None:
    lowered = path.lower()
    for name, prefixes in _LAYER_RULES:
        if any(p in lowered for p in prefixes):
            return name
    return None


def _violates(from_layer: str, to_layer: str) -> bool:
    """A violation is an edge that points *upward* in the rule list."""
    if from_layer == "tests" or to_layer == "tests":
        return False  # tests can depend on anything
    if from_layer == "other" or to_layer == "other":
        return False
    return _LAYER_INDEX.get(from_layer, 99) > _LAYER_INDEX.get(to_layer, 99)


def _render_mermaid(
    layers: tuple[ArchitectureLayer, ...],
    cross: dict[tuple[str, str], int],
) -> str:
    """Render a Mermaid flowchart with one node per layer."""
    lines: list[str] = ["flowchart TB"]
    if not layers:
        lines.append('  empty["(no files classified)"]')
        return "\n".join(lines)
    for layer in layers:
        lines.append(f'  {layer.name}["{layer.name}<br/>{len(layer.file_paths)} files"]')
    for (a, b), count in sorted(cross.items()):
        lines.append(f"  {a} -->|{count}| {b}")
    return "\n".join(lines)
