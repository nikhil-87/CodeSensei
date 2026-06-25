"""Worker-side exceptions."""
from __future__ import annotations


class WorkerError(Exception):
    """Base class for worker errors."""


class JobNotFoundError(WorkerError):
    """The DB does not contain the AnalysisJob the task was given."""


class RepositoryNotFoundError(WorkerError):
    """The DB does not contain the Repository the task was given."""


class IndexingDegraded(WorkerError):
    """Indexing failed but analysis succeeded — non-fatal, surfaced for tests."""
