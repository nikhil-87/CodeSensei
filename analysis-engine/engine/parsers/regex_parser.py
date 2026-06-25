"""Regex-based fallback parser.

Tree-sitter is the right tool for production-grade multi-language parsing
but it's a heavy dependency to make mandatory. This module provides a
deliberate, conservative regex-based pass that handles the most common
languages well enough to populate symbol/import tables and approximate
complexity. It is *always* available — used both as the explicit parser
for languages we don't have a richer one for, and as a fallback when a
richer parser raises.

What it can do:
    * Find top-level functions / classes / types in JS/TS/Java/Go/Rust/C/C++.
    * Extract import / require / use statements.
    * Approximate cyclomatic complexity by counting branch keywords.

What it deliberately does *not* do:
    * Resolve types or symbols across files.
    * Distinguish methods from functions inside class bodies (everything
      defined inside a class is reported as a ``method``).
"""
from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass

from engine.parsers.base import ParseInput, ParseOutput
from engine.results import Import, Symbol


@dataclass(frozen=True)
class _LangRules:
    """Per-language regex rule bundle."""

    function_patterns: tuple[re.Pattern[str], ...]
    class_patterns: tuple[re.Pattern[str], ...]
    import_patterns: tuple[re.Pattern[str], ...]
    branch_keywords: tuple[str, ...]


# Compiled once at import time.
_BRANCH_KEYWORDS_C_FAMILY: tuple[str, ...] = (
    "if", "else if", "for", "while", "case", "&&", "||", "?",
)
_BRANCH_KEYWORDS_GO: tuple[str, ...] = (
    "if", "for", "case", "switch", "select", "&&", "||",
)
_BRANCH_KEYWORDS_RUST: tuple[str, ...] = (
    "if", "match", "for", "while", "&&", "||",
)

# Names we *never* report as symbols even if a regex captures them.
# These are language keywords / control-flow constructs that look like
# function calls (``if (cond) { ... }``).
_RESERVED_NAMES: frozenset[str] = frozenset(
    {
        "if", "else", "for", "while", "do", "switch", "case", "default",
        "return", "break", "continue", "throw", "try", "catch", "finally",
        "async", "await", "new", "yield", "typeof", "instanceof",
        "public", "private", "protected", "static", "final", "abstract",
        "const", "let", "var", "function", "class", "interface", "type",
        "enum", "struct", "trait", "impl", "mod", "use", "package", "import",
        "export", "from", "as", "in", "of", "is", "and", "or", "not",
        "true", "false", "null", "undefined", "None", "True", "False",
    }
)


_RULES: dict[str, _LangRules] = {
    # ---- JavaScript / TypeScript ----
    "javascript": _LangRules(
        function_patterns=(
            re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.M),
            re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\(", re.M),
            re.compile(r"^\s*(?:export\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{", re.M),
        ),
        class_patterns=(
            re.compile(r"^\s*(?:export\s+(?:default\s+)?)?class\s+(\w+)", re.M),
        ),
        import_patterns=(
            re.compile(r"""^\s*import\s+(?:[\w*\s{},]+\s+from\s+)?['"]([^'"]+)['"]""", re.M),
            re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)""", re.M),
        ),
        branch_keywords=_BRANCH_KEYWORDS_C_FAMILY,
    ),
    "typescript": _LangRules(
        function_patterns=(
            re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*[<(]", re.M),
            re.compile(r"^\s*(?:export\s+)?const\s+(\w+)\s*[:=]\s*(?:async\s*)?[(<]", re.M),
            re.compile(r"^\s*(?:public|private|protected)?\s*(?:async\s+)?(\w+)\s*\([^)]*\)\s*[:{]", re.M),
        ),
        class_patterns=(
            re.compile(r"^\s*(?:export\s+(?:default\s+)?)?(?:abstract\s+)?class\s+(\w+)", re.M),
            re.compile(r"^\s*(?:export\s+)?interface\s+(\w+)", re.M),
            re.compile(r"^\s*(?:export\s+)?type\s+(\w+)(?:\s*<[^>]+>)?\s*=", re.M),
        ),
        import_patterns=(
            re.compile(r"""^\s*import\s+(?:type\s+)?(?:[\w*\s{},]+\s+from\s+)?['"]([^'"]+)['"]""", re.M),
            re.compile(r"""\brequire\(\s*['"]([^'"]+)['"]\s*\)""", re.M),
        ),
        branch_keywords=_BRANCH_KEYWORDS_C_FAMILY,
    ),
    # ---- Java ----
    "java": _LangRules(
        function_patterns=(
            re.compile(
                r"^\s*(?:public|private|protected|static|final|abstract|synchronized|\s)+"
                r"[\w<>\[\],\s]+?\s+(\w+)\s*\([^)]*\)\s*(?:throws[\w\s,]+)?\{",
                re.M,
            ),
        ),
        class_patterns=(
            re.compile(r"^\s*(?:public\s+|private\s+|protected\s+)?(?:abstract\s+|final\s+)?class\s+(\w+)", re.M),
            re.compile(r"^\s*(?:public\s+|private\s+|protected\s+)?interface\s+(\w+)", re.M),
            re.compile(r"^\s*(?:public\s+|private\s+|protected\s+)?enum\s+(\w+)", re.M),
        ),
        import_patterns=(
            re.compile(r"^\s*import\s+(?:static\s+)?([\w.*]+)\s*;", re.M),
        ),
        branch_keywords=_BRANCH_KEYWORDS_C_FAMILY,
    ),
    # ---- Go ----
    "go": _LangRules(
        function_patterns=(
            re.compile(r"^\s*func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(", re.M),
        ),
        class_patterns=(
            re.compile(r"^\s*type\s+(\w+)\s+(?:struct|interface)\b", re.M),
        ),
        import_patterns=(
            re.compile(r"""^\s*import\s+\(\s*([^)]+)\)""", re.M | re.S),
            re.compile(r"""^\s*import\s+(?:\w+\s+)?['"]([^'"]+)['"]""", re.M),
        ),
        branch_keywords=_BRANCH_KEYWORDS_GO,
    ),
    # ---- Rust ----
    "rust": _LangRules(
        function_patterns=(
            re.compile(r"^\s*(?:pub(?:\([^)]+\))?\s+)?(?:async\s+)?fn\s+(\w+)", re.M),
        ),
        class_patterns=(
            re.compile(r"^\s*(?:pub(?:\([^)]+\))?\s+)?(?:struct|enum|trait)\s+(\w+)", re.M),
        ),
        import_patterns=(
            re.compile(r"^\s*use\s+([\w:{}*,\s]+)\s*;", re.M),
        ),
        branch_keywords=_BRANCH_KEYWORDS_RUST,
    ),
    # ---- C / C++ ----
    "c": _LangRules(
        function_patterns=(
            re.compile(r"^\s*[\w*\s]+\s+(\w+)\s*\([^)]*\)\s*\{", re.M),
        ),
        class_patterns=(
            re.compile(r"^\s*(?:typedef\s+)?(?:struct|union|enum)\s+(\w+)", re.M),
        ),
        import_patterns=(
            re.compile(r"""^\s*#\s*include\s*[<"]([^>"]+)[>"]""", re.M),
        ),
        branch_keywords=_BRANCH_KEYWORDS_C_FAMILY,
    ),
    "cpp": _LangRules(
        function_patterns=(
            re.compile(r"^\s*[\w:*&\s<>,]+\s+(\w+)\s*\([^)]*\)\s*(?:const)?\s*\{", re.M),
        ),
        class_patterns=(
            re.compile(r"^\s*(?:template\s*<[^>]+>\s*)?(?:class|struct)\s+(\w+)", re.M),
        ),
        import_patterns=(
            re.compile(r"""^\s*#\s*include\s*[<"]([^>"]+)[>"]""", re.M),
        ),
        branch_keywords=_BRANCH_KEYWORDS_C_FAMILY,
    ),
    # ---- C# ----
    "csharp": _LangRules(
        function_patterns=(
            re.compile(
                r"^\s*(?:public|private|protected|internal|static|virtual|override|async|\s)+"
                r"[\w<>\[\],\s]+\s+(\w+)\s*\([^)]*\)\s*\{",
                re.M,
            ),
        ),
        class_patterns=(
            re.compile(r"^\s*(?:public|private|internal|sealed|abstract|\s)*class\s+(\w+)", re.M),
            re.compile(r"^\s*(?:public|private|internal|\s)*interface\s+(\w+)", re.M),
        ),
        import_patterns=(
            re.compile(r"^\s*using\s+([\w.]+)\s*;", re.M),
        ),
        branch_keywords=_BRANCH_KEYWORDS_C_FAMILY,
    ),
    # ---- Ruby / PHP / others left as no-symbol but still LOC counted ----
}


class RegexParser:
    """Single class that handles many languages via the rule table above."""

    name = "regex"

    @property
    def languages(self) -> tuple[str, ...]:
        return tuple(_RULES.keys())

    def parse(self, payload: ParseInput) -> ParseOutput:
        rules = _RULES.get(payload.language)
        if rules is None:
            # Unknown language: still emit something useful (zero counts).
            return ParseOutput(
                symbols=(),
                imports=(),
                cyclomatic=1,
                cognitive=0,
                function_count=0,
                class_count=0,
                parser_name=self.name,
            )

        source = payload.source
        symbols = tuple(
            self._match_symbols(source, rules.function_patterns, kind="function")
        ) + tuple(
            self._match_symbols(source, rules.class_patterns, kind="class")
        )
        imports = tuple(self._match_imports(source, rules.import_patterns))
        function_count = sum(1 for s in symbols if s.kind == "function")
        class_count = sum(1 for s in symbols if s.kind == "class")
        cyclomatic = self._cyclomatic(source, rules.branch_keywords)
        cognitive = max(0, cyclomatic - 1)  # very rough proxy

        return ParseOutput(
            symbols=symbols,
            imports=imports,
            cyclomatic=cyclomatic,
            cognitive=cognitive,
            function_count=function_count,
            class_count=class_count,
            parser_name=self.name,
        )

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------
    @staticmethod
    def _line_of(source: str, match: re.Match[str]) -> int:
        return source.count("\n", 0, match.start()) + 1

    def _match_symbols(
        self,
        source: str,
        patterns: tuple[re.Pattern[str], ...],
        *,
        kind: str,
    ) -> Iterator[Symbol]:
        seen: set[tuple[str, int]] = set()
        for pattern in patterns:
            for match in pattern.finditer(source):
                name = match.group(1).strip()
                if not name or not name[0].isalpha() and name[0] != "_":
                    continue
                if name in _RESERVED_NAMES:
                    continue
                line = self._line_of(source, match)
                key = (name, line)
                if key in seen:
                    continue
                seen.add(key)
                yield Symbol(
                    name=name,
                    kind=kind,
                    line_start=line,
                    line_end=line,
                    qualified_name=None,
                    is_exported=not name.startswith("_"),
                )

    def _match_imports(
        self,
        source: str,
        patterns: tuple[re.Pattern[str], ...],
    ) -> Iterator[Import]:
        seen: set[tuple[str, int]] = set()
        for pattern in patterns:
            for match in pattern.finditer(source):
                raw = match.group(1).strip()
                # Go's grouped-import block: split on whitespace.
                for item in re.split(r"\s+", raw):
                    item = item.strip().strip("\"'")
                    if not item:
                        continue
                    line = self._line_of(source, match)
                    key = (item, line)
                    if key in seen:
                        continue
                    seen.add(key)
                    yield Import(
                        module=item,
                        line=line,
                        is_relative=item.startswith("."),
                    )

    @staticmethod
    def _cyclomatic(source: str, keywords: tuple[str, ...]) -> int:
        count = 1
        for kw in keywords:
            # \b for alphabetic keywords; literal match for symbol operators.
            if kw.isalpha():
                pattern = rf"\b{re.escape(kw)}\b"
            else:
                pattern = re.escape(kw)
            count += len(re.findall(pattern, source))
        return count
