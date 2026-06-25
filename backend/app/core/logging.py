"""Structured JSON logging via structlog.

- One JSON line per log event in production; pretty console in dev.
- Every event automatically carries `request_id` when emitted inside a request.
- Secret-like keys are redacted before serialization.
"""
from __future__ import annotations

import logging
import re
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from app.core.config import Settings

# Keys whose values are scrubbed before they reach any sink.
_REDACT_PATTERN = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|authorization|cookie)",
    re.IGNORECASE,
)
_REDACTED = "***REDACTED***"


def _redact_processor(_: Any, __: str, event_dict: EventDict) -> EventDict:
    """Redact sensitive values from the event dict before render."""
    for key in list(event_dict.keys()):
        if _REDACT_PATTERN.search(key):
            event_dict[key] = _REDACTED
    return event_dict


def configure_logging(settings: Settings) -> None:
    """Idempotent logging configuration. Call once at app startup."""
    level = getattr(logging, settings.app_log_level)

    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        _redact_processor,
    ]

    if settings.is_production or settings.app_env == "staging":
        renderer: Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Re-route stdlib logging through structlog so uvicorn / SQLAlchemy logs are uniform.
    handler = logging.StreamHandler()
    handler.setFormatter(_StdlibBridgeFormatter(shared_processors, renderer))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)

    for noisy in ("uvicorn.access", "sqlalchemy.engine.Engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


class _StdlibBridgeFormatter(logging.Formatter):
    def __init__(self, shared: list[Processor], renderer: Processor) -> None:
        super().__init__()
        self._processors = [*shared, renderer]

    def format(self, record: logging.LogRecord) -> str:
        event_dict: EventDict = {
            "event": record.getMessage(),
            "logger": record.name,
            "level": record.levelname.lower(),
        }
        if record.exc_info:
            event_dict["exc_info"] = record.exc_info
        for processor in self._processors:
            event_dict = processor(None, record.levelname.lower(), event_dict)  # type: ignore[assignment,arg-type]
        return event_dict if isinstance(event_dict, str) else str(event_dict)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Module-level logger accessor."""
    return structlog.get_logger(name)
