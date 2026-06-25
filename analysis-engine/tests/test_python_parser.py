"""Python AST parser — accuracy on realistic code."""
from __future__ import annotations

from engine.parsers.base import ParseInput
from engine.parsers.python_parser import PythonAstParser


SAMPLE = '''\
"""Module docstring."""
from __future__ import annotations

import os
from collections import defaultdict
from . import sibling
from .. import grandparent

GLOBAL_CONST = 42


def public_func(x: int) -> int:
    if x > 0 and x < 10:
        return x
    elif x == 0:
        return 0
    else:
        for i in range(x):
            if i % 2:
                continue
        return -1


async def _private_async() -> None:
    return None


class MyClass:
    def method_one(self) -> int:
        return 1

    async def method_two(self) -> int:
        try:
            return await self._inner()
        except ValueError:
            return -1

    def _hidden(self) -> None:
        pass


class _PrivateClass:
    pass
'''


def test_python_parser_extracts_symbols() -> None:
    parser = PythonAstParser()
    out = parser.parse(
        ParseInput(relative_path="m.py", source=SAMPLE, language="python")
    )

    by_kind: dict[str, list[str]] = {}
    for sym in out.symbols:
        by_kind.setdefault(sym.kind, []).append(sym.name)

    assert "MyClass" in by_kind["class"]
    assert "_PrivateClass" in by_kind["class"]
    assert "public_func" in by_kind["function"]
    assert "_private_async" in by_kind["function"]
    assert "method_one" in by_kind["method"]
    assert "method_two" in by_kind["method"]
    assert "_hidden" in by_kind["method"]


def test_python_parser_qualifies_method_names() -> None:
    parser = PythonAstParser()
    out = parser.parse(
        ParseInput(relative_path="m.py", source=SAMPLE, language="python")
    )
    method_one = next(s for s in out.symbols if s.name == "method_one")
    assert method_one.qualified_name == "MyClass.method_one"


def test_python_parser_extracts_imports_and_relativity() -> None:
    parser = PythonAstParser()
    out = parser.parse(
        ParseInput(relative_path="m.py", source=SAMPLE, language="python")
    )
    modules = {imp.module for imp in out.imports}
    assert "os" in modules
    assert "collections" in modules
    # Relative imports preserve their leading dots.
    relative = [imp for imp in out.imports if imp.is_relative]
    assert {".sibling", "..grandparent"} <= {imp.module for imp in relative} or any(
        imp.module.startswith(".") for imp in relative
    )


def test_python_parser_complexity_is_positive_for_branchy_code() -> None:
    parser = PythonAstParser()
    out = parser.parse(
        ParseInput(relative_path="m.py", source=SAMPLE, language="python")
    )
    assert out.cyclomatic > 5
    assert out.cognitive > 0
    assert out.function_count >= 4
    assert out.class_count == 2


def test_python_parser_handles_syntax_errors_gracefully() -> None:
    parser = PythonAstParser()
    out = parser.parse(
        ParseInput(
            relative_path="bad.py",
            source="def broken(:\n    pass\n",
            language="python",
        )
    )
    assert out.symbols == ()
    assert out.imports == ()
    assert out.cyclomatic == 1
