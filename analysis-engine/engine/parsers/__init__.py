"""Parser plug-ins.

Public surface: :class:`Parser` (protocol), :class:`ParseInput`,
:class:`ParseOutput`, :func:`get_parser_registry`.
"""
from engine.parsers.base import ParseInput, ParseOutput, Parser
from engine.parsers.registry import get_parser_registry

__all__ = ["ParseInput", "ParseOutput", "Parser", "get_parser_registry"]
