"""Result dataclasses returned by the engine.

These are *plain* dataclasses (no SQLAlchemy, no Pydantic) so the engine
stays usable from any consumer — including a CLI, the worker, or tests.
The worker owns persistence; the engine owns analysis.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Symbol:
    """A named, locatable construct in the source code."""

    name: str
    kind: str  # function | method | class | interface | struct | enum | variable | constant | type_alias | module
    line_start: int
    line_end: int
    qualified_name: str | None = None
    is_exported: bool = True


@dataclass(frozen=True, slots=True)
class Import:
    """A raw import statement before resolution to a concrete file path.

    Resolution happens in :class:`engine.graph.builder.GraphBuilder` once
    every file's exports are known.
    """

    module: str  # textual import target ("os.path", "./utils", "lodash")
    line: int
    is_relative: bool = False


@dataclass(frozen=True, slots=True)
class FileMetrics:
    """Per-file numeric metrics."""

    cyclomatic: int
    cognitive: int
    lines_of_code: int
    function_count: int
    class_count: int


@dataclass(frozen=True, slots=True)
class FileAnalysis:
    """Everything we know about a single source file."""

    path: str  # repo-relative, forward-slashes
    language: str | None
    size_bytes: int
    line_count: int
    sha256: str
    symbols: tuple[Symbol, ...]
    imports: tuple[Import, ...]
    metrics: FileMetrics
    parser: str  # "python_ast" | "tree_sitter:python" | "regex" | ...


@dataclass(frozen=True, slots=True)
class DependencyEdge:
    """A *resolved* dependency between two files in the repository."""

    from_path: str
    to_path: str
    kind: str  # import | inheritance | call | instantiation | reference
    symbol: str | None = None
    line: int | None = None


@dataclass(frozen=True, slots=True)
class DeadCodeFinding:
    """A symbol the engine believes is unused."""

    file_path: str
    symbol_name: str
    kind: str
    line_start: int
    confidence: float  # 0..1
    reason: str


@dataclass(frozen=True, slots=True)
class ArchitectureLayer:
    """A discovered architectural layer with its constituent files."""

    name: str
    file_paths: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ArchitectureReport:
    """Layer assignments + violations + a Mermaid diagram body."""

    layers: tuple[ArchitectureLayer, ...]
    violations: tuple[str, ...]  # human-readable
    mermaid: str


@dataclass(frozen=True, slots=True)
class RepositoryAnalysis:
    """Top-level aggregate. Worker persists this in chunks."""

    files: tuple[FileAnalysis, ...]
    dependencies: tuple[DependencyEdge, ...]
    cycles: tuple[tuple[str, ...], ...]
    languages: dict[str, int] = field(default_factory=dict)
    total_lines: int = 0
    dead_code: tuple[DeadCodeFinding, ...] = ()
    architecture: ArchitectureReport | None = None

    @property
    def file_count(self) -> int:
        return len(self.files)
