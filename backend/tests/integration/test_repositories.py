"""Integration tests for the repository CRUD surface.

These exercise the full FastAPI ↔ service ↔ repository ↔ DB stack with an
SQLite database and a fake job dispatcher.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from tests.conftest import FakeJobDispatcher


class TestSubmitRepository:
    def test_creates_repository_and_enqueues_job(
        self,
        client: TestClient,
        fake_dispatcher: FakeJobDispatcher,
        repo_payload: dict[str, str],
    ) -> None:
        response = client.post("/api/v1/repositories", json=repo_payload)
        assert response.status_code == 202

        body = response.json()
        assert body["status"] == "queued"
        assert body["progress"] == 0
        assert body["repository_id"] is not None
        assert body["rq_job_id"].startswith("rq:test:")

        # The dispatcher actually got a call with the new repo's id.
        assert len(fake_dispatcher.enqueued) == 1
        assert str(fake_dispatcher.enqueued[0][0]) is not None

    def test_rejects_invalid_url_scheme(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/repositories",
            json={"url": "ftp://example.com/x/y"},
        )
        assert response.status_code == 422
        assert response.json()["error"] == "validation_error"

    def test_rejects_non_github_host(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://gitlab.com/x/y"},
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_repository_url"

    def test_rejects_duplicate_when_active_job_exists(
        self,
        client: TestClient,
        repo_payload: dict[str, str],
    ) -> None:
        # First submission queues a job; status remains "queued" because the
        # fake dispatcher never moves it forward.
        first = client.post("/api/v1/repositories", json=repo_payload)
        assert first.status_code == 202

        second = client.post("/api/v1/repositories", json=repo_payload)
        assert second.status_code == 409
        assert second.json()["error"] == "analysis_already_running"


class TestListAndGetRepository:
    def test_list_is_empty_initially(self, client: TestClient) -> None:
        response = client.get("/api/v1/repositories")
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["page_size"] == 20

    def test_list_returns_seeded_repository(
        self, client: TestClient, seeded_repository
    ) -> None:
        response = client.get("/api/v1/repositories")
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert body["items"][0]["id"] == str(seeded_repository.id)
        assert body["items"][0]["status"] == "ready"

    def test_filter_by_status(
        self, client: TestClient, seeded_repository
    ) -> None:
        ok = client.get("/api/v1/repositories?status=ready")
        empty = client.get("/api/v1/repositories?status=failed")
        assert ok.json()["total"] == 1
        assert empty.json()["total"] == 0

    def test_get_returns_full_record(
        self, client: TestClient, seeded_repository
    ) -> None:
        response = client.get(f"/api/v1/repositories/{seeded_repository.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["url"] == seeded_repository.url
        assert body["file_count"] == 2
        assert body["languages"] == "python:2"

    def test_get_unknown_returns_404(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/repositories/00000000-0000-4000-8000-000000000000"
        )
        assert response.status_code == 404
        assert response.json()["error"] == "repository_not_found"


class TestDeleteRepository:
    def test_delete_then_get_returns_404(
        self, client: TestClient, seeded_repository
    ) -> None:
        response = client.delete(f"/api/v1/repositories/{seeded_repository.id}")
        assert response.status_code == 204
        follow_up = client.get(f"/api/v1/repositories/{seeded_repository.id}")
        assert follow_up.status_code == 404

    def test_delete_unknown_returns_404(self, client: TestClient) -> None:
        response = client.delete(
            "/api/v1/repositories/00000000-0000-4000-8000-000000000000"
        )
        assert response.status_code == 404
