"""Parser registry — maps language → parser, with graceful fallback."""
from __future__ import annotations

from functools import lru_cache

from engine.parsers.base import ParseInput, ParseOutput, Parser
from engine.parsers.python_parser import PythonAstParser
from engine.parsers.regex_parser import RegexParser
from engine.parsers.tree_sitter_parser import get_tree_sitter_parser


class ParserRegistry:
    """Resolves a parser for a given language and runs it defensively.

    Resolution order:
        1. Native parser (currently ``PythonAstParser``).
        2. Tree-sitter parser (if installed and supports the language).
        3. Regex fallback (always available).

    The registry also wraps every ``parse`` call in a ``try``/``except`` so
    that a single broken file cannot fail an entire repository run.
    """

    def __init__(self) -> None:
        self._regex = RegexParser()
        self._python = PythonAstParser()
        self._tree_sitter = get_tree_sitter_parser()

        self._by_language: dict[str, Parser] = {}
        for lang in self._python.languages:
            self._by_language[lang] = self._python
        if self._tree_sitter is not None:
            for lang in self._tree_sitter.languages:
                self._by_language.setdefault(lang, self._tree_sitter)
        for lang in self._regex.languages:
            self._by_language.setdefault(lang, self._regex)

    def parse(self, payload: ParseInput) -> ParseOutput:
        parser = self._by_language.get(payload.language)
        if parser is None:
            return _empty(self._regex.name)
        try:
            return parser.parse(payload)
        except Exception:  # noqa: BLE001 — never let a single file crash a run
            try:
                return self._regex.parse(payload)
            except Exception:  # noqa: BLE001
                return _empty(self._regex.name)

    def supported_languages(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_language.keys()))


def _empty(parser_name: str) -> ParseOutput:
    return ParseOutput(
        symbols=(),
        imports=(),
        cyclomatic=1,
        cognitive=0,
        function_count=0,
        class_count=0,
        parser_name=parser_name,
    )


@lru_cache(maxsize=1)
def get_parser_registry() -> ParserRegistry:
    """Process-wide singleton — building the registry is non-trivial."""
    return ParserRegistry()
