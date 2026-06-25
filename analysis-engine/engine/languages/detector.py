"""Map files to canonical language names.

We deliberately keep the mapping small and explicit. ``linguist`` would be
more accurate but we don't need that level of fidelity to drive the
parsers — and adding a Ruby gem dependency to a Python project is
unjustifiable.
"""
from __future__ import annotations

from pathlib import Path

# Canonical language names. Used as keys in the parser registry so they
# *must* match values returned here verbatim.
_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".scala": "scala",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "scss",
    ".less": "less",
    ".md": "markdown",
    ".rst": "restructuredtext",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".sql": "sql",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".tf": "terraform",
    ".hcl": "terraform",
}

_SPECIAL_NAMES: dict[str, str] = {
    "dockerfile": "dockerfile",
    "makefile": "make",
    "rakefile": "ruby",
    "gemfile": "ruby",
}


def detect_language(extension: str) -> str | None:
    """Return the canonical language name for an extension, or ``None``."""
    return _EXT_TO_LANGUAGE.get(extension.lower())


def language_for_path(path: Path) -> str | None:
    """Combine extension + filename heuristics."""
    ext = path.suffix.lower()
    if ext in _EXT_TO_LANGUAGE:
        return _EXT_TO_LANGUAGE[ext]
    return _SPECIAL_NAMES.get(path.name.lower())
