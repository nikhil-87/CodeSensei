"""Outbound ports — protocols the engine calls into.

Keeping these as :class:`typing.Protocol` lets the worker, the CLI, and
tests inject anything compatible without forcing a runtime base class.
"""
from __future__ import annotations

from typing import Protocol


class ProgressReporter(Protocol):
    """Receives progress notifications during a run.

    Implementations must be thread-safe — the engine may call from any
    thread (parser threads in particular).
    """

    def stage(self, name: str, message: str | None = None) -> None: ...

    def progress(
        self, fraction: float, message: str | None = None
    ) -> None: ...  # 0..1

    def file_done(self, path: str) -> None: ...


class NullProgressReporter:
    """Default no-op reporter used when callers don't pass one."""

    def stage(self, name: str, message: str | None = None) -> None:
        return None

    def progress(self, fraction: float, message: str | None = None) -> None:
        return None

    def file_done(self, path: str) -> None:
        return None
