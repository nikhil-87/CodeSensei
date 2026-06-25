"""Worker entry point — ``python -m worker.app`` starts an RQ worker.

The dispatcher in the backend enqueues a function by string
(``worker.app.tasks.analyze_repository.run``); RQ resolves that import
path on the worker side every time it consumes a job. We don't pre-import
the task here because doing so would tie this entry point to the engine's
import-time side-effects (parser registry warm-up, etc.) — RQ already
handles that lazily.
"""
from __future__ import annotations

import signal
import socket
import sys
import time

import redis
import structlog
from rq import Connection, Queue, SimpleWorker

from worker.app.db import init_engine
from worker.app.logging_config import configure_logging
from worker.app.metrics import serve_metrics
from worker.app.settings import get_settings

# Best-effort version probe — the worker is installed as a package, so
# importlib.metadata works in containers and editable installs alike.
try:
    from importlib.metadata import version as _pkg_version

    _VERSION = _pkg_version("codesensei-worker")
except Exception:  # noqa: BLE001
    _VERSION = "0.0.0"

# Global flag for graceful shutdown
_shutdown_requested = False


def _handle_shutdown(signum: int, frame) -> None:
    """Signal handler for graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True


def main(argv: list[str] | None = None) -> int:
    global _shutdown_requested

    cfg = get_settings()
    configure_logging(cfg.app_log_level)
    log = structlog.get_logger("worker")

    # Fail fast if the selected AI providers are missing required credentials.
    from shared.config.providers import validate_provider_config

    provider_errors = validate_provider_config(
        llm_provider=cfg.llm_provider,
        embedding_provider=cfg.embedding_provider,
        groq_api_key=cfg.groq_api_key,
        huggingface_api_key=cfg.huggingface_api_key,
    )
    if provider_errors:
        for err in provider_errors:
            log.error("invalid_provider_config", error=err)
        return 1

    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)

    init_engine(cfg)  # fail fast if Postgres is unreachable

    if cfg.metrics_enabled:
        try:
            serve_metrics(cfg.metrics_port, version=_VERSION)
        except OSError as exc:
            # Don't fail the worker just because the metrics port is busy.
            log.warning("metrics_server_unavailable", error=str(exc))

    log.info(
        "worker_starting",
        queue=cfg.redis_queue_name,
        concurrency=cfg.worker_concurrency,
    )

    # Polling interval - how often to check for jobs (must be < 15s for Upstash)
    poll_interval = cfg.worker_poll_interval_seconds

    while not _shutdown_requested:
        try:
            # Create fresh connection for each poll cycle to avoid idle timeout
            connection = redis.Redis.from_url(
                cfg.redis_url,
                socket_timeout=cfg.redis_socket_timeout,
                socket_connect_timeout=cfg.redis_socket_connect_timeout,
                socket_keepalive=True,
                socket_keepalive_options={
                    socket.TCP_KEEPIDLE: cfg.redis_keepalive_idle,
                    socket.TCP_KEEPINTVL: cfg.redis_keepalive_interval,
                    socket.TCP_KEEPCNT: cfg.redis_keepalive_count,
                },
                retry_on_timeout=True,
            )
            connection.ping()

            with Connection(connection):
                queue = Queue(name=cfg.redis_queue_name)
                worker = SimpleWorker(
                    [queue],
                    name=f"codesensei-worker-{queue.name}",
                    default_result_ttl=cfg.worker_rq_result_ttl,
                )

                # Use burst mode - processes available jobs then exits
                # This avoids the pubsub channel that times out on Upstash
                worker.work(
                    burst=True,
                    logging_level=cfg.app_log_level,
                )

            # Close connection after burst to prevent idle timeout
            connection.close()

        except redis.exceptions.RedisError as exc:
            log.warning("redis_error_retrying", error=str(exc))
            time.sleep(poll_interval)
            continue

        except Exception as exc:
            log.error("worker_error", error=str(exc))
            time.sleep(poll_interval)
            continue

        # Sleep before next poll cycle
        if not _shutdown_requested:
            time.sleep(poll_interval)

    log.info("worker_shutting_down")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
