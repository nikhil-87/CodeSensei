"""CodeSensei — analysis engine package.

Pure-Python code analysis. No HTTP, no database, no async runtime: the
engine takes a path on disk and returns dataclasses describing the
repository's structure, symbols, dependencies, metrics, dead code, and
architecture.

Public API
----------
:func:`engine.analyze`             — One-shot, synchronous entry point.
:class:`engine.RepositoryAnalysis` — The fully aggregated result.
:class:`engine.AnalysisOptions`    — Tunable knobs (timeouts, limits).
:class:`engine.ProgressReporter`   — Callback protocol for progress events.
"""
from __future__ import annotations

from engine.orchestrator import AnalysisOptions, AnalysisOrchestrator, analyze
from engine.ports import NullProgressReporter, ProgressReporter
from engine.results import (
    DependencyEdge,
    FileAnalysis,
    FileMetrics,
    Import,
    RepositoryAnalysis,
    Symbol,
)

__version__ = "0.1.0"

__all__ = [
    "AnalysisOptions",
    "AnalysisOrchestrator",
    "DependencyEdge",
    "FileAnalysis",
    "FileMetrics",
    "Import",
    "NullProgressReporter",
    "ProgressReporter",
    "RepositoryAnalysis",
    "Symbol",
    "__version__",
    "analyze",
]
