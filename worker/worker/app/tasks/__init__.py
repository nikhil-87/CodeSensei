"""Worker tasks. Each module exposes a top-level ``run`` callable.

RQ resolves callables by their fully-qualified import path
(``worker.app.tasks.analyze_repository.run``) — the backend's
JobDispatcher refers to that exact string.
"""
