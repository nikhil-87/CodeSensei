"""Prometheus metrics for the worker.

The worker is a long-running process that consumes RQ jobs. We expose a
small HTTP endpoint on a side port (default 9101) so Prometheus can scrape
job-level counters and histograms without disturbing the queue.

Metric naming follows the OpenMetrics convention:
* ``_total`` suffix on monotonic counters
* ``_seconds`` suffix on time-valued histograms
* ``_bytes`` / ``_count`` for absolute gauges

The ``status`` label on the analysis counter takes the values
``succeeded``/``failed``; finer-grained error categories are emitted as
log fields rather than label cardinality.
"""
from __future__ import annotations

import time
from contextlib import contextmanager
from collections.abc import Iterator

import structlog
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    start_http_server,
)

logger = structlog.get_logger(__name__)

REGISTRY = CollectorRegistry(auto_describe=True)

# ---------------------------------------------------------------------------
# Job-level metrics
# ---------------------------------------------------------------------------
analysis_jobs_processed_total = Counter(
    "worker_analysis_jobs_processed_total",
    "Total analysis jobs processed by the worker.",
    labelnames=("status",),
    registry=REGISTRY,
)

analysis_job_duration_seconds = Histogram(
    "worker_analysis_job_duration_seconds",
    "Wall-clock duration of an end-to-end analysis job.",
    buckets=(1, 5, 15, 30, 60, 120, 300, 600, 1200, 1800, 3600),
    registry=REGISTRY,
)

analysis_files_processed_total = Counter(
    "worker_analysis_files_processed_total",
    "Total files persisted across all analysis jobs.",
    registry=REGISTRY,
)

analysis_chunks_indexed_total = Counter(
    "worker_analysis_chunks_indexed_total",
    "Total embedding chunks indexed across all analysis jobs.",
    registry=REGISTRY,
)

worker_jobs_in_flight = Gauge(
    "worker_jobs_in_flight",
    "Number of analysis jobs currently being processed by this worker.",
    registry=REGISTRY,
)

worker_build_info = Gauge(
    "worker_build_info",
    "Build / version info as labels; value is always 1.",
    labelnames=("version",),
    registry=REGISTRY,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@contextmanager
def track_analysis_job() -> Iterator[None]:
    """Record duration + in-flight gauge around an analysis run.

    Status counter is *not* incremented here — the caller knows whether
    the run succeeded or raised before reaching the persist phase, and
    we don't want to count partially-failed runs as either.
    """
    worker_jobs_in_flight.inc()
    start = time.perf_counter()
    try:
        yield
    finally:
        analysis_job_duration_seconds.observe(time.perf_counter() - start)
        worker_jobs_in_flight.dec()


def record_job_outcome(*, succeeded: bool) -> None:
    analysis_jobs_processed_total.labels(
        status="succeeded" if succeeded else "failed"
    ).inc()


def record_files_processed(count: int) -> None:
    if count > 0:
        analysis_files_processed_total.inc(count)


def record_chunks_indexed(count: int) -> None:
    if count > 0:
        analysis_chunks_indexed_total.inc(count)


# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
def serve_metrics(port: int, *, version: str) -> None:
    """Start the Prometheus exposition server on ``port`` (background thread)."""
    worker_build_info.labels(version=version).set(1)
    start_http_server(port, registry=REGISTRY)
    logger.info("worker_metrics_server_started", port=port)
