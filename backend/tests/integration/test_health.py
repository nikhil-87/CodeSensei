"""Smoke tests — `/healthz`, OpenAPI schema, basic 404 / validation flows."""
from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz_is_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body


def test_openapi_schema_lists_versioned_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/v1/repositories" in paths
    assert "/api/v1/repositories/{repository_id}" in paths
    assert "/api/v1/repositories/{repository_id}/analyze" in paths


def test_submit_validates_url(client: TestClient) -> None:
    response = client.post(
        "/api/v1/repositories",
        json={"url": "ftp://example.com/x/y", "branch": "main"},
    )
    # Pydantic rejects the URL scheme at the schema layer → 422
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "validation_error"


def test_missing_repository_returns_domain_error(client: TestClient) -> None:
    # Random UUID we know doesn't exist
    response = client.get("/api/v1/repositories/00000000-0000-4000-8000-000000000000")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "repository_not_found"
