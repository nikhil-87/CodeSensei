"""Tree-sitter-based parser, used when the package is available.

We import lazily so the engine doesn't crash if ``tree-sitter-languages``
isn't installed (developer machines, slim docker images). When unavailable
the registry simply doesn't register us and the regex fallback handles
the languages.

The implementation is intentionally minimal — Tree-sitter gives us
parse-error tolerance and accurate ranges; deeper queries (resolving
identifiers, types, scopes) are out of scope for v1.
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from engine.parsers.base import ParseInput, ParseOutput
from engine.parsers.regex_parser import RegexParser
from engine.results import Import, Symbol


# Languages we *try* to load. Each entry maps the engine's canonical name to
# the tree-sitter-languages key.
_TREE_SITTER_LANGUAGES: dict[str, str] = {
    "javascript": "javascript",
    "typescript": "typescript",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "csharp": "c_sharp",
    "ruby": "ruby",
}


def _try_import_tree_sitter() -> Any | None:
    try:  # noqa: SIM105 — explicit fall-through is clearer here
        from tree_sitter_languages import get_parser  # type: ignore[import-not-found]
        return get_parser
    except Exception:  # noqa: BLE001 — any failure means "not available"
        return None


class TreeSitterParser:
    """Wraps tree-sitter parsers with the same shape as our other parsers.

    Falls back to :class:`RegexParser` for the *fact extraction* even when
    tree-sitter is available — implementing language-aware queries for nine
    languages is its own project. What tree-sitter buys us today is:

    * **Robust LOC / branch counting** — we walk only "real" code nodes,
      ignoring strings/comments. This is materially more accurate than
      regex on languages with heavy template strings (TS/JS/Rust).
    * **Future extensibility** — when v2 wants accurate symbol ranges,
      this is the plug-in point.
    """

    name = "tree_sitter"

    def __init__(self) -> None:
        get_parser = _try_import_tree_sitter()
        self._parsers: dict[str, Any] = {}
        if get_parser is None:
            return
        for canonical, ts_name in _TREE_SITTER_LANGUAGES.items():
            try:
                self._parsers[canonical] = get_parser(ts_name)
            except Exception:  # noqa: BLE001
                # Some platforms ship without certain bindings; skip silently.
                continue
        self._regex = RegexParser()

    @property
    def available(self) -> bool:
        return bool(self._parsers)

    @property
    def languages(self) -> tuple[str, ...]:
        return tuple(self._parsers.keys())

    def parse(self, payload: ParseInput) -> ParseOutput:
        ts_parser = self._parsers.get(payload.language)
        if ts_parser is None:  # pragma: no cover — registry guards this
            return self._regex.parse(payload)

        # Use regex extraction for symbols/imports (cheap, sufficient for v1)
        # but use tree-sitter to refine the cyclomatic count.
        regex_out = self._regex.parse(payload)
        try:
            tree = ts_parser.parse(payload.source.encode("utf-8"))
        except Exception:  # noqa: BLE001
            return regex_out

        cyclomatic = _count_branches(tree.root_node)
        cognitive = _count_cognitive(tree.root_node)
        return ParseOutput(
            symbols=regex_out.symbols,
            imports=regex_out.imports,
            cyclomatic=max(1, cyclomatic),
            cognitive=cognitive,
            function_count=regex_out.function_count,
            class_count=regex_out.class_count,
            parser_name=f"{self.name}:{payload.language}",
        )


# ---------------------------------------------------------------------------
# Tree-sitter walking helpers
# ---------------------------------------------------------------------------
# Node types treated as cyclomatic decision points across the supported langs.
_DECISION_TYPES: frozenset[str] = frozenset(
    {
        "if_statement",
        "if_expression",
        "else_clause",
        "for_statement",
        "for_in_statement",
        "for_each_statement",
        "while_statement",
        "do_statement",
        "switch_statement",
        "switch_case",
        "case_clause",
        "ternary_expression",
        "conditional_expression",
        "logical_and",
        "logical_or",
        "binary_expression",  # filtered below by operator
        "match_expression",
        "match_arm",
        "catch_clause",
        "except_clause",
        "&&",
        "||",
    }
)


def _walk(node: Any) -> Iterator[Any]:
    yield node
    for child in node.children:
        yield from _walk(child)


def _count_branches(root: Any) -> int:
    count = 1
    for node in _walk(root):
        if node.type in _DECISION_TYPES:
            count += 1
    return count


def _count_cognitive(root: Any) -> int:
    """Cognitive complexity = sum over nesting levels of decision points.

    A breadth-first walk would be more accurate; this depth-aware DFS is a
    close approximation that's cheap to compute.
    """
    score = 0

    def _recurse(node: Any, depth: int) -> None:
        nonlocal score
        if node.type in _DECISION_TYPES:
            score += 1 + depth
            depth += 1
        for child in node.children:
            _recurse(child, depth)

    _recurse(root, 0)
    return score


# Module-level singleton used by the registry.
_INSTANCE: TreeSitterParser | None = None


def get_tree_sitter_parser() -> TreeSitterParser | None:
    """Return a parser instance if tree-sitter is usable, else ``None``."""
    global _INSTANCE  # noqa: PLW0603 — intentional module-level cache
    if _INSTANCE is None:
        candidate = TreeSitterParser()
        _INSTANCE = candidate if candidate.available else None
    return _INSTANCE
