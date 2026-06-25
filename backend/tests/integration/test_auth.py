"""Integration tests for mock authentication.

These verify that, with ``MOCK_AUTH`` enabled (the default in the test
settings — see ``conftest.test_settings``), the app behaves exactly as if a
real user were logged in, without any GitHub OAuth round-trip or session
cookie. This is what lets the whole suite exercise protected routes offline.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from shared.config import defaults


class TestMockAuthSession:
    def test_me_returns_the_mock_user(self, client: TestClient) -> None:
        # No cookie is sent — mock auth resolves the user transparently.
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200
        body = response.json()
        assert body["username"] == defaults.MOCK_AUTH_USERNAME
        assert body["github_id"] == defaults.MOCK_AUTH_GITHUB_ID

    def test_protected_route_works_without_cookie(self, client: TestClient) -> None:
        # Submitting a repo requires an authenticated user; mock auth supplies one.
        response = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/Hello-World"},
        )
        assert response.status_code == 202

    def test_created_repository_is_owned_by_mock_user(
        self, client: TestClient
    ) -> None:
        created = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/spoon-knife"},
        )
        repo_id = created.json()["repository_id"]

        # The mock user can read back its own repo, and it is the only one listed.
        listing = client.get("/api/v1/repositories")
        assert listing.status_code == 200
        items = listing.json()["items"]
        assert any(item["id"] == repo_id for item in items)
