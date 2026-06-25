"""Engine errors — raised on hard failures (clone, oversize, etc.)."""
from __future__ import annotations


class EngineError(Exception):
    """Base class for all engine-raised exceptions."""


class CloneError(EngineError):
    """Failed to clone a repository (git command failure, network, etc.)."""


class RepositoryTooLargeError(EngineError):
    """Repository exceeds configured size or file-count limits."""


class UnsupportedRepositoryError(EngineError):
    """Repository is structurally something we cannot analyse (empty, binary)."""


class ParserError(EngineError):
    """A specific parser raised an exception we choose to surface."""
