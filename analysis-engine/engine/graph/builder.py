"""Build a file-level dependency graph from per-file parse outputs.

The parsers emit *raw* import targets (``"./utils"``, ``"os.path"``,
``"github.com/foo/bar"``). The graph builder resolves those into concrete
file paths inside the repository, where possible. Imports we cannot
resolve to a local file (third-party / stdlib) are silently dropped — the
graph models *intra-repository* coupling.

The algorithm:
    1. Build an index of every analyzable file path.
    2. For each file's imports, try a small set of resolution strategies
       in order (relative path → module path → bare-name fuzzy match).
    3. Emit at most one edge per (from, to, kind, line) tuple.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import PurePosixPath

from engine.results import DependencyEdge, FileAnalysis


# File extensions tried when resolving an import target without one.
_EXT_FALLBACKS: tuple[str, ...] = (
    ".py", ".pyi",
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".go", ".rs", ".java", ".kt", ".cs",
    ".c", ".h", ".cpp", ".hpp",
)


class GraphBuilder:
    """Resolves cross-file references from parser-level imports."""

    def __init__(self, files: Iterable[FileAnalysis]) -> None:
        self._files: tuple[FileAnalysis, ...] = tuple(files)
        self._by_path: dict[str, FileAnalysis] = {f.path: f for f in self._files}
        self._by_basename: dict[str, list[str]] = defaultdict(list)
        self._by_module: dict[str, str] = {}
        for f in self._files:
            base = PurePosixPath(f.path).stem
            self._by_basename[base].append(f.path)
            for module_path in _module_aliases(f.path):
                self._by_module.setdefault(module_path, f.path)

    def build(self) -> tuple[DependencyEdge, ...]:
        edges: list[DependencyEdge] = []
        seen: set[tuple[str, str, str, int | None]] = set()

        for file in self._files:
            for imp in file.imports:
                target = self._resolve(file.path, imp.module, imp.is_relative)
                if target is None or target == file.path:
                    continue
                key = (file.path, target, "import", imp.line)
                if key in seen:
                    continue
                seen.add(key)
                edges.append(
                    DependencyEdge(
                        from_path=file.path,
                        to_path=target,
                        kind="import",
                        symbol=None,
                        line=imp.line,
                    )
                )
        return tuple(edges)

    # ------------------------------------------------------------------
    # resolution strategies
    # ------------------------------------------------------------------
    def _resolve(self, from_path: str, module: str, is_relative: bool) -> str | None:
        if not module:
            return None

        if is_relative or module.startswith("."):
            return self._resolve_relative(from_path, module)

        # Try as a Python-style dotted module first.
        if "." in module and "/" not in module:
            converted = module.replace(".", "/")
            if (resolved := self._lookup_with_extensions(converted)) is not None:
                return resolved
            if (resolved := self._by_module.get(converted)) is not None:
                return resolved

        # Try as a slash-style path (JS/TS/Go-relative-to-module).
        if "/" in module:
            stripped = module.lstrip("/")
            if (resolved := self._lookup_with_extensions(stripped)) is not None:
                return resolved

        # Last resort: basename match (only if unambiguous).
        candidates = self._by_basename.get(module)
        if candidates and len(candidates) == 1:
            return candidates[0]
        return None

    def _resolve_relative(self, from_path: str, module: str) -> str | None:
        # Count leading dots → number of parents to walk up.
        leading = 0
        while leading < len(module) and module[leading] == ".":
            leading += 1
        rest = module[leading:].lstrip("/.")

        from_dir = PurePosixPath(from_path).parent
        for _ in range(max(0, leading - 1)):
            if from_dir == PurePosixPath("."):
                break
            from_dir = from_dir.parent

        target = (from_dir / rest.replace(".", "/")).as_posix() if rest else from_dir.as_posix()
        return self._lookup_with_extensions(target)

    def _lookup_with_extensions(self, candidate: str) -> str | None:
        if candidate in self._by_path:
            return candidate
        for ext in _EXT_FALLBACKS:
            full = f"{candidate}{ext}"
            if full in self._by_path:
                return full
            # Index file (``__init__.py`` / ``index.ts`` / ``mod.rs``)
            for index in (f"{candidate}/__init__{ext}",
                          f"{candidate}/index{ext}",
                          f"{candidate}/mod{ext}"):
                if index in self._by_path:
                    return index
        return None


def _module_aliases(file_path: str) -> Iterable[str]:
    """Yield the dotted/slashed paths a given file might be imported as."""
    p = PurePosixPath(file_path)
    parts = p.with_suffix("").parts
    yield "/".join(parts)
    if parts and parts[-1] in {"__init__", "index", "mod"}:
        yield "/".join(parts[:-1])
