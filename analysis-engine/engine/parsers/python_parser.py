"""High-fidelity Python parser using the stdlib :mod:`ast`.

Produces:
    * Module / class / function symbols (with qualified names).
    * Imports (absolute and relative).
    * Cyclomatic complexity (McCabe).
    * Cognitive complexity (Sonar's formulation, simplified).
    * Function / class counts.
"""
from __future__ import annotations

import ast

from engine.parsers.base import ParseInput, ParseOutput
from engine.results import Import, Symbol


class PythonAstParser:
    name = "python_ast"
    languages: tuple[str, ...] = ("python",)

    def parse(self, payload: ParseInput) -> ParseOutput:
        try:
            tree = ast.parse(payload.source, filename=payload.relative_path)
        except SyntaxError:
            # Don't fail the whole run; downstream uses the regex fallback.
            return _empty(self.name)

        collector = _Collector(payload.source)
        collector.visit(tree)

        return ParseOutput(
            symbols=tuple(collector.symbols),
            imports=tuple(collector.imports),
            cyclomatic=collector.cyclomatic,
            cognitive=collector.cognitive,
            function_count=collector.function_count,
            class_count=collector.class_count,
            parser_name=self.name,
        )


# ---------------------------------------------------------------------------
# AST visitor
# ---------------------------------------------------------------------------
_DECISION_NODES: tuple[type[ast.AST], ...] = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.ExceptHandler,
    ast.With,
    ast.AsyncWith,
    ast.BoolOp,
    ast.IfExp,
    ast.comprehension,
    ast.Match,
    ast.match_case,
)


class _Collector(ast.NodeVisitor):
    """Single-pass AST walk that produces every fact we need."""

    def __init__(self, source: str) -> None:
        self._source = source  # currently unused, retained for future range hints
        self.symbols: list[Symbol] = []
        self.imports: list[Import] = []
        self.cyclomatic: int = 1
        self.cognitive: int = 0
        self.function_count: int = 0
        self.class_count: int = 0

        self._scope_stack: list[str] = []
        self._nesting_depth: int = 0

    # ----- imports --------------------------------------------------------
    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802 — stdlib API
        for alias in node.names:
            self.imports.append(
                Import(module=alias.name, line=node.lineno, is_relative=False)
            )

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        is_relative = (node.level or 0) > 0
        # Preserve the leading dots so the graph builder can resolve them.
        prefix = "." * (node.level or 0)
        module = (node.module or "").strip()
        full = f"{prefix}{module}" if module else prefix
        if full:
            self.imports.append(
                Import(module=full, line=node.lineno, is_relative=is_relative)
            )

    # ----- definitions ----------------------------------------------------
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._handle_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._handle_function(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self.class_count += 1
        qualified = self._qualified(node.name)
        self.symbols.append(
            Symbol(
                name=node.name,
                kind="class",
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno) or node.lineno,
                qualified_name=qualified,
                is_exported=not node.name.startswith("_"),
            )
        )
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    # ----- complexity counters --------------------------------------------
    def generic_visit(self, node: ast.AST) -> None:
        if isinstance(node, _DECISION_NODES):
            self.cyclomatic += _cyclomatic_weight(node)
            self.cognitive += 1 + self._nesting_depth

        opens_nesting = isinstance(
            node,
            (
                ast.If,
                ast.For,
                ast.AsyncFor,
                ast.While,
                ast.Try,
                ast.With,
                ast.AsyncWith,
                ast.FunctionDef,
                ast.AsyncFunctionDef,
                ast.ClassDef,
                ast.Match,
            ),
        )
        if opens_nesting:
            self._nesting_depth += 1
            super().generic_visit(node)
            self._nesting_depth -= 1
        else:
            super().generic_visit(node)

    # ----- helpers --------------------------------------------------------
    def _handle_function(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> None:
        self.function_count += 1
        kind = "method" if self._scope_stack else "function"
        qualified = self._qualified(node.name)
        self.symbols.append(
            Symbol(
                name=node.name,
                kind=kind,
                line_start=node.lineno,
                line_end=getattr(node, "end_lineno", node.lineno) or node.lineno,
                qualified_name=qualified,
                is_exported=not node.name.startswith("_"),
            )
        )
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def _qualified(self, name: str) -> str:
        if not self._scope_stack:
            return name
        return ".".join((*self._scope_stack, name))


def _cyclomatic_weight(node: ast.AST) -> int:
    """Weight for cyclomatic complexity contribution.

    ``BoolOp`` adds one per additional operand (each ``and``/``or`` is a
    decision point). Everything else adds 1.
    """
    if isinstance(node, ast.BoolOp):
        return max(1, len(node.values) - 1)
    return 1


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
