"""Walks a cloned repository and yields the files we should analyse.

Honours ``.gitignore``, skips known vendor / build directories, skips
binary content (detected by sniffing the first 8 KB), and enforces a
per-file size cap to keep parser memory bounded.
"""
from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pathspec

# Directories we never descend into. Kept conservative — if a project really
# does keep first-party code in ``vendor/`` they can rename it; the platform
# is opinionated.
_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "bower_components",
        "vendor",
        "third_party",
        "build",
        "dist",
        "out",
        "target",
        "bin",
        "obj",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".gradle",
        ".terraform",
        "coverage",
        ".next",
        ".nuxt",
        ".cache",
    }
)

# A first-pass extension allow-list. The language detector applies the
# authoritative mapping later; this is just to skip obvious binaries fast.
_TEXT_EXTENSIONS: frozenset[str] = frozenset(
    {
        ".py", ".pyi", ".pyx",
        ".js", ".jsx", ".mjs", ".cjs",
        ".ts", ".tsx",
        ".java", ".kt", ".kts",
        ".go", ".rs",
        ".c", ".h", ".cpp", ".hpp", ".cc", ".hh",
        ".cs", ".rb", ".php", ".swift", ".scala",
        ".sh", ".bash", ".zsh", ".ps1",
        ".html", ".css", ".scss", ".sass", ".less",
        ".md", ".rst", ".txt",
        ".json", ".yaml", ".yml", ".toml", ".ini",
        ".sql", ".graphql", ".gql",
        ".dockerfile", ".tf", ".hcl",
    }
)


@dataclass(frozen=True, slots=True)
class WalkedFile:
    """A file the walker emitted."""

    absolute_path: Path
    relative_path: str  # forward-slashes, repo-relative
    size_bytes: int


@dataclass(frozen=True)
class WalkOptions:
    """Knobs for the walker."""

    max_file_bytes: int = 2 * 1024 * 1024  # 2 MB hard cap
    max_total_files: int = 5000
    follow_symlinks: bool = False


class FileWalker:
    """Iterates the candidate source files in a cloned repository."""

    def __init__(self, root: Path, options: WalkOptions | None = None) -> None:
        self._root = root.resolve()
        self._options = options or WalkOptions()
        self._gitignore = self._load_gitignore(self._root)

    def walk(self) -> Iterator[WalkedFile]:
        """Yield :class:`WalkedFile` items in deterministic order."""
        emitted = 0
        # We do our own walk so we can prune SKIP_DIRS up-front (much faster
        # on big monorepos than a post-filter).
        stack: list[Path] = [self._root]
        while stack:
            current = stack.pop()
            try:
                children = sorted(current.iterdir())
            except (OSError, PermissionError):
                continue

            for child in children:
                if child.is_symlink() and not self._options.follow_symlinks:
                    continue
                if child.is_dir():
                    if child.name in _SKIP_DIRS:
                        continue
                    if self._gitignored(child, is_dir=True):
                        continue
                    stack.append(child)
                    continue

                if not child.is_file():
                    continue
                if self._gitignored(child, is_dir=False):
                    continue
                if not self._has_text_extension(child):
                    continue

                try:
                    size = child.stat().st_size
                except OSError:
                    continue
                if size == 0 or size > self._options.max_file_bytes:
                    continue

                if self._looks_binary(child):
                    continue

                rel = child.relative_to(self._root).as_posix()
                emitted += 1
                if emitted > self._options.max_total_files:
                    return
                yield WalkedFile(
                    absolute_path=child, relative_path=rel, size_bytes=size
                )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    @staticmethod
    def _load_gitignore(root: Path) -> pathspec.PathSpec | None:
        gi = root / ".gitignore"
        if not gi.exists():
            return None
        try:
            patterns = gi.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return None
        return pathspec.PathSpec.from_lines("gitwildmatch", patterns)

    def _gitignored(self, path: Path, *, is_dir: bool) -> bool:
        if self._gitignore is None:
            return False
        rel = path.relative_to(self._root).as_posix()
        if is_dir:
            rel += "/"
        return self._gitignore.match_file(rel)

    @staticmethod
    def _has_text_extension(path: Path) -> bool:
        ext = path.suffix.lower()
        if ext in _TEXT_EXTENSIONS:
            return True
        # Dockerfile and Makefile have no extension.
        return path.name.lower() in {"dockerfile", "makefile", "rakefile", "gemfile"}

    @staticmethod
    def _looks_binary(path: Path, sniff_bytes: int = 8192) -> bool:
        """Heuristic: presence of NUL byte → binary."""
        try:
            with path.open("rb") as fh:
                chunk = fh.read(sniff_bytes)
        except OSError:
            return True
        return b"\x00" in chunk
