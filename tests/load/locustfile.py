"""Locust load profile for the CodeSensei backend.

Run from the repo root:

    locust -f tests/load/locustfile.py \\
           --host http://localhost:8000 \\
           --users 50 --spawn-rate 5 --run-time 2m

The user mix targets the read-heavy paths a real dashboard hits — list +
detail + insights — with occasional analysis submissions. A small fraction
of the run probes ``/healthz`` so we can spot regressions in the cheap path.
"""
from __future__ import annotations

import random
import uuid
from typing import Any

from locust import HttpUser, between, task


def _maybe_repo_id(response: Any) -> str | None:
    try:
        body = response.json()
    except ValueError:
        return None
    items = body.get("items") if isinstance(body, dict) else None
    if not items:
        return None
    return items[0].get("id")


class DashboardUser(HttpUser):
    """Browses the dashboard. Reads dominate writes 9:1."""

    wait_time = between(0.5, 3.0)

    repo_id: str | None = None

    def on_start(self) -> None:
        # Cache one repo id for subsequent detail/insights calls.
        with self.client.get(
            "/api/v1/repositories",
            name="GET /repositories",
            catch_response=True,
        ) as response:
            self.repo_id = _maybe_repo_id(response)

    # --- read-heavy tasks ----------------------------------------------------
    @task(8)
    def list_repositories(self) -> None:
        self.client.get(
            "/api/v1/repositories?page=1&page_size=20",
            name="GET /repositories",
        )

    @task(4)
    def get_repository(self) -> None:
        if not self.repo_id:
            return
        self.client.get(
            f"/api/v1/repositories/{self.repo_id}",
            name="GET /repositories/{id}",
        )

    @task(3)
    def dependency_graph(self) -> None:
        if not self.repo_id:
            return
        self.client.get(
            f"/api/v1/repositories/{self.repo_id}/dependencies",
            name="GET /repositories/{id}/dependencies",
        )

    @task(2)
    def complexity(self) -> None:
        if not self.repo_id:
            return
        self.client.get(
            f"/api/v1/repositories/{self.repo_id}/complexity?top_n=10",
            name="GET /repositories/{id}/complexity",
        )

    @task(2)
    def dead_code(self) -> None:
        if not self.repo_id:
            return
        self.client.get(
            f"/api/v1/repositories/{self.repo_id}/dead-code",
            name="GET /repositories/{id}/dead-code",
        )

    @task(1)
    def healthz(self) -> None:
        self.client.get("/healthz", name="GET /healthz")

    # --- low-frequency writes ------------------------------------------------
    @task(1)
    def submit_repository(self) -> None:
        owner = random.choice(["octocat", "torvalds", "django", "fastapi"])
        slug = f"load-{uuid.uuid4().hex[:8]}"
        self.client.post(
            "/api/v1/repositories",
            name="POST /repositories",
            json={"url": f"https://github.com/{owner}/{slug}"},
        )
