"""End-to-end pipeline: clone → walk → parse → graph → metrics → result.

This is the engine's public entry point. It is *synchronous* by design —
the worker (Phase 5) puts it on a thread; tests call it directly.
"""
from __future__ import annotations

import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import structlog

from engine.architecture.classifier import classify_architecture
from engine.cloning.git_cloner import CloneOptions, GitCloner
from engine.dead_code.detector import detect_dead_code
from engine.exceptions import EngineError, UnsupportedRepositoryError
from engine.graph.builder import GraphBuilder
from engine.graph.cycles import detect_cycles
from engine.languages.detector import language_for_path
from engine.parsers.base import ParseInput
from engine.parsers.registry import get_parser_registry
from engine.ports import NullProgressReporter, ProgressReporter
from engine.results import (
    DependencyEdge,
    FileAnalysis,
    FileMetrics,
    RepositoryAnalysis,
)
from engine.walker.file_walker import FileWalker, WalkOptions
from engine import _defaults

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class AnalysisOptions:
    """All configuration the orchestrator needs."""

    workspace_root: Path
    branch: str | None = None
    clone_depth: int = _defaults.CLONE_DEPTH
    clone_timeout_seconds: int = _defaults.CLONE_TIMEOUT_SECONDS
    max_repo_size_mb: int = _defaults.API_MAX_REPO_SIZE_MB
    max_files: int = _defaults.API_MAX_REPO_FILES
    max_file_bytes: int = _defaults.API_MAX_FILE_BYTES
    parse_workers: int = _defaults.ENGINE_PARSE_WORKERS


class AnalysisOrchestrator:
    """Coordinates the engine's stages."""

    def __init__(
        self,
        options: AnalysisOptions,
        reporter: ProgressReporter | None = None,
    ) -> None:
        self._options = options
        self._reporter = reporter or NullProgressReporter()
        self._registry = get_parser_registry()

    # ------------------------------------------------------------------
    # Public surface
    # ------------------------------------------------------------------
    def run(self, github_url: str) -> RepositoryAnalysis:
        """Full pipeline. Returns a fully-populated :class:`RepositoryAnalysis`."""
        clone_path = self._clone(github_url)
        walked = self._walk(clone_path)
        if not walked:
            raise UnsupportedRepositoryError(
                "Repository contains no analyzable source files"
            )
        files = self._parse_all(clone_path, walked)
        return self._aggregate(files)

    def run_on_path(self, repository_path: Path) -> RepositoryAnalysis:
        """Skip cloning — analyse a directory that already exists on disk.

        Used for tests, the CLI, and re-analyses where the worker has already
        cloned the workspace.
        """
        walked = self._walk(repository_path)
        if not walked:
            raise UnsupportedRepositoryError(
                "Repository contains no analyzable source files"
            )
        files = self._parse_all(repository_path, walked)
        return self._aggregate(files)

    # ------------------------------------------------------------------
    # Stages
    # ------------------------------------------------------------------
    def _clone(self, github_url: str) -> Path:
        self._reporter.stage("clone", f"Cloning {github_url}")
        cloner = GitCloner(
            CloneOptions(
                workspace_root=self._options.workspace_root,
                branch=self._options.branch,
                depth=self._options.clone_depth,
                timeout_seconds=self._options.clone_timeout_seconds,
                max_size_mb=self._options.max_repo_size_mb,
            )
        )
        return cloner.clone(github_url)

    def _walk(self, repository_path: Path) -> list[Path]:
        self._reporter.stage("walk", "Discovering files")
        walker = FileWalker(
            repository_path,
            WalkOptions(
                max_file_bytes=self._options.max_file_bytes,
                max_total_files=self._options.max_files,
            ),
        )
        return [w.absolute_path for w in walker.walk()]

    def _parse_all(
        self, repository_path: Path, files: list[Path]
    ) -> tuple[FileAnalysis, ...]:
        self._reporter.stage("parse", f"Parsing {len(files)} files")

        results: list[FileAnalysis] = []
        with ThreadPoolExecutor(max_workers=self._options.parse_workers) as pool:
            futures = {
                pool.submit(self._parse_one, repository_path, path): path
                for path in files
            }
            total = len(futures)
            done = 0
            for future in as_completed(futures):
                done += 1
                try:
                    result = future.result()
                except Exception as exc:  # noqa: BLE001
                    path = futures[future]
                    logger.warning(
                        "parse_failed", path=str(path), error=str(exc)
                    )
                    continue
                if result is None:
                    continue
                results.append(result)
                self._reporter.file_done(result.path)
                if total:
                    self._reporter.progress(done / total)

        # Deterministic ordering simplifies tests + diffing across runs.
        results.sort(key=lambda f: f.path)
        return tuple(results)

    def _parse_one(
        self, repository_path: Path, absolute: Path
    ) -> FileAnalysis | None:
        try:
            raw = absolute.read_bytes()
        except OSError as exc:
            logger.debug("read_failed", path=str(absolute), error=str(exc))
            return None

        text = _decode(raw)
        if text is None:
            return None

        relative = absolute.relative_to(repository_path).as_posix()
        language = language_for_path(absolute)
        line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
        sha = hashlib.sha256(raw).hexdigest()

        if language is None:
            metrics = FileMetrics(
                cyclomatic=0,
                cognitive=0,
                lines_of_code=line_count,
                function_count=0,
                class_count=0,
            )
            return FileAnalysis(
                path=relative,
                language=None,
                size_bytes=len(raw),
                line_count=line_count,
                sha256=sha,
                symbols=(),
                imports=(),
                metrics=metrics,
                parser="none",
            )

        out = self._registry.parse(
            ParseInput(relative_path=relative, source=text, language=language)
        )
        metrics = FileMetrics(
            cyclomatic=out.cyclomatic,
            cognitive=out.cognitive,
            lines_of_code=line_count,
            function_count=out.function_count,
            class_count=out.class_count,
        )
        return FileAnalysis(
            path=relative,
            language=language,
            size_bytes=len(raw),
            line_count=line_count,
            sha256=sha,
            symbols=out.symbols,
            imports=out.imports,
            metrics=metrics,
            parser=out.parser_name,
        )

    def _aggregate(
        self, files: tuple[FileAnalysis, ...]
    ) -> RepositoryAnalysis:
        self._reporter.stage("aggregate", "Building dependency graph")

        edges: tuple[DependencyEdge, ...] = GraphBuilder(files).build()
        cycles = detect_cycles((f.path for f in files), edges)

        self._reporter.stage("dead_code", "Scanning for dead code")
        dead_code = detect_dead_code(files, edges)

        self._reporter.stage("architecture", "Classifying layers")
        architecture = classify_architecture(files, edges)

        languages: dict[str, int] = {}
        total_lines = 0
        for f in files:
            total_lines += f.line_count
            if f.language is not None:
                languages[f.language] = languages.get(f.language, 0) + 1

        return RepositoryAnalysis(
            files=files,
            dependencies=edges,
            cycles=cycles,
            languages=languages,
            total_lines=total_lines,
            dead_code=dead_code,
            architecture=architecture,
        )


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------
def analyze(
    github_url_or_path: str | Path,
    options: AnalysisOptions,
    reporter: ProgressReporter | None = None,
) -> RepositoryAnalysis:
    """One-shot convenience wrapper.

    If passed a ``Path``, skips cloning. Otherwise treats it as a URL.
    """
    orchestrator = AnalysisOrchestrator(options, reporter)
    if isinstance(github_url_or_path, Path):
        return orchestrator.run_on_path(github_url_or_path)
    return orchestrator.run(github_url_or_path)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _decode(raw: bytes) -> str | None:
    """Best-effort UTF-8 decoding with chardet fallback."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        pass
    try:
        import chardet  # local import — chardet is a heavy module
        guess = chardet.detect(raw[:32_000])
        encoding = guess.get("encoding") or "latin-1"
    except Exception:  # noqa: BLE001
        encoding = "latin-1"
    try:
        return raw.decode(encoding, errors="replace")
    except (LookupError, UnicodeDecodeError):
        return None


# Silence noisy GitPython logger to keep our structured logs clean.
logging.getLogger("git").setLevel(logging.WARNING)


__all__ = [
    "AnalysisOptions",
    "AnalysisOrchestrator",
    "EngineError",
    "analyze",
]
