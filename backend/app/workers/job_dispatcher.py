"""JobDispatcher — thin abstraction over RQ for enqueueing analysis jobs.

The actual job function lives in the `worker/` service. The backend never
imports it; it enqueues by name (string) so the worker package can evolve
independently. The worker registers a function named
``worker.app.tasks.analyze_repository.run`` which RQ resolves dynamically
when consuming the queue.
"""
from __future__ import annotations

import uuid
from typing import Any

import redis
import structlog
from rq import Queue
from rq.job import Job

from app.core.config import Settings
from app.core.exceptions import QueueUnavailableError

logger = structlog.get_logger(__name__)

# The fully-qualified callable name the worker registers under.
ANALYZE_REPOSITORY_JOB = "worker.app.tasks.analyze_repository.run"


class JobDispatcher:
    """Encapsulates enqueue semantics so services depend on a stable contract."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._connection: redis.Redis | None = None
        self._queue: Queue | None = None

    # ----- lifecycle ------------------------------------------------------
    def _ensure_queue(self) -> Queue:
        if self._queue is not None:
            return self._queue
        try:
            self._connection = redis.Redis.from_url(
                self._settings.redis_url,
                socket_timeout=self._settings.redis_socket_timeout,
                socket_connect_timeout=self._settings.redis_socket_connect_timeout,
            )
            self._connection.ping()
            self._queue = Queue(
                name=self._settings.redis_queue_name,
                connection=self._connection,
                default_timeout=self._settings.worker_job_timeout_seconds,
            )
            return self._queue
        except redis.exceptions.RedisError as exc:
            logger.error("queue_unavailable", error=str(exc))
            raise QueueUnavailableError("Redis queue is unreachable") from exc

    # ----- public API ------------------------------------------------------
    def enqueue_analysis(
        self,
        repository_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> str:
        queue = self._ensure_queue()
        try:
            rq_job: Job = queue.enqueue(
                ANALYZE_REPOSITORY_JOB,
                kwargs={"repository_id": str(repository_id), "job_id": str(job_id)},
                retry=None,  # retry policy lives inside the worker task
                job_id=f"analysis:{job_id}",
                description=f"Analyze repository {repository_id}",
            )
        except redis.exceptions.RedisError as exc:
            logger.error("enqueue_failed", error=str(exc))
            raise QueueUnavailableError("Failed to enqueue analysis job") from exc
        logger.info(
            "analysis_job_enqueued",
            repository_id=str(repository_id),
            job_id=str(job_id),
            rq_job_id=rq_job.id,
        )
        return rq_job.id

    def queue_depth(self) -> int:
        try:
            return int(self._ensure_queue().count)
        except QueueUnavailableError:
            return -1

    def healthcheck(self) -> dict[str, Any]:
        try:
            depth = self.queue_depth()
            return {"status": "ok", "queue_depth": depth}
        except QueueUnavailableError as exc:
            return {"status": "error", "message": str(exc)}
