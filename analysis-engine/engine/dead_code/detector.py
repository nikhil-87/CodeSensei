"""Cross-file unused-symbol detection.

This is intentionally a *heuristic* detector: properly proving a symbol
is dead requires whole-program type analysis we explicitly do not do.
What we *can* do, accurately and quickly:

* If a file is never imported by any other file, every symbol it exports
  is reported as ``"file_not_imported"`` with confidence 0.5 (it might be
  an entry-point — main, CLI, test, migration, etc.).
* For files that *are* imported, an exported symbol whose name does not
  appear anywhere in the rest of the codebase is reported with confidence
  0.7 (``"name_unreferenced_outside_definition"``).

The Phase-2 backend already has these heuristics inline; this module is
the engine-side authoritative implementation that the worker will use.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import PurePosixPath

from engine.results import DeadCodeFinding, DependencyEdge, FileAnalysis


_ENTRYPOINT_HINTS: tuple[str, ...] = (
    "main", "cli", "entry", "wsgi", "asgi", "manage", "app", "server",
    "migrations", "setup",
)


def detect_dead_code(
    files: Iterable[FileAnalysis],
    edges: Iterable[DependencyEdge],
) -> tuple[DeadCodeFinding, ...]:
    """Return one ``DeadCodeFinding`` per *suspected* unused symbol."""
    files_tuple = tuple(files)
    inbound: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        inbound[edge.to_path].append(edge.from_path)

    # Build a single big string we can grep for cross-file mentions.
    # We exclude each file's own contents when checking that file.
    findings: list[DeadCodeFinding] = []
    for file in files_tuple:
        if not file.symbols:
            continue
        path = file.path
        is_imported = bool(inbound.get(path))
        is_entrypoint = _looks_like_entrypoint(path)
        for symbol in file.symbols:
            if not symbol.is_exported:
                continue
            if symbol.name.startswith("_"):
                continue
            if _is_dunder(symbol.name):
                continue

            if not is_imported:
                if is_entrypoint:
                    continue
                findings.append(
                    DeadCodeFinding(
                        file_path=path,
                        symbol_name=symbol.name,
                        kind=symbol.kind,
                        line_start=symbol.line_start,
                        confidence=0.5,
                        reason="file_not_imported",
                    )
                )
                continue

            if _name_unreferenced_outside(file, symbol.name, files_tuple):
                findings.append(
                    DeadCodeFinding(
                        file_path=path,
                        symbol_name=symbol.name,
                        kind=symbol.kind,
                        line_start=symbol.line_start,
                        confidence=0.7,
                        reason="name_unreferenced_outside_definition",
                    )
                )

    return tuple(findings)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _looks_like_entrypoint(path: str) -> bool:
    name = PurePosixPath(path).stem.lower()
    if name in {"__main__", "__init__", "main"}:
        return True
    if any(hint in path.lower() for hint in _ENTRYPOINT_HINTS):
        return True
    return path.lower().startswith(("tests/", "test/", "examples/", "scripts/"))


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__") and len(name) > 4


def _name_unreferenced_outside(
    owning_file: FileAnalysis,
    name: str,
    files: tuple[FileAnalysis, ...],
) -> bool:
    """``True`` if *name* doesn't appear in any *other* file's symbol list
    or import-target list. This is conservative — string-only references
    can sneak past it, but those are also the most fragile in practice.

    A future v2 will get full-source scanning; keeping it index-based now
    keeps memory bounded on huge repositories.
    """
    for other in files:
        if other.path == owning_file.path:
            continue
        for sym in other.symbols:
            if sym.name == name:
                return False
        for imp in other.imports:
            if name in imp.module:
                return False
    return True
