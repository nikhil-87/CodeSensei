"""Parser protocol and the data each parser sees / returns."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from engine.results import Import, Symbol


@dataclass(frozen=True, slots=True)
class ParseInput:
    """Everything a parser needs to do its job."""

    relative_path: str
    source: str  # decoded text content
    language: str


@dataclass(frozen=True, slots=True)
class ParseOutput:
    """The structured facts a parser produced about a file."""

    symbols: tuple[Symbol, ...]
    imports: tuple[Import, ...]
    cyclomatic: int
    cognitive: int
    function_count: int
    class_count: int
    parser_name: str


class Parser(Protocol):
    """All parsers implement this single method.

    Parsers MUST be defensive: any exception thrown here will be caught and
    the file will be re-parsed with the regex fallback. Returning an empty
    ``ParseOutput`` is acceptable for files we cannot understand.
    """

    name: str
    languages: tuple[str, ...]

    def parse(self, payload: ParseInput) -> ParseOutput: ...
