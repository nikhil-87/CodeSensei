"""Integration tests for the read-only insight endpoints.

These rely on the ``seeded_repository`` fixture in conftest.py, which
inserts a small but realistic graph of files / symbols / metrics.
"""
from __future__ import annotations

from fastapi.testclient import TestClient


class TestDependencyGraph:
    def test_returns_graph_with_nodes_and_edges(
        self, client: TestClient, seeded_repository
    ) -> None:
        response = client.get(
            f"/api/v1/repositories/{seeded_repository.id}/dependencies"
        )
        assert response.status_code == 200
        body = response.json()
        assert body["repository_id"] == str(seeded_repository.id)
        assert len(body["nodes"]) == 2
        assert len(body["edges"]) == 1
        assert body["edges"][0]["kind"] == "import"
        # Cycles list exists (and is empty for this acyclic seed).
        assert body["cycles"] == []
        # Degree calculation
        node_by_path = {n["path"]: n for n in body["nodes"]}
        assert node_by_path["src/a.py"]["out_degree"] == 1
        assert node_by_path["src/b.py"]["in_degree"] == 1


class TestComplexity:
    def test_returns_top_files_sorted_by_cyclomatic(
        self, client: TestClient, seeded_repository
    ) -> None:
        response = client.get(
            f"/api/v1/repositories/{seeded_repository.id}/complexity"
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["top_files"]) == 2
        # File a.py has cyclomatic 14, b.py has 3 — a.py should come first.
        assert body["top_files"][0]["path"] == "src/a.py"
        assert body["top_files"][0]["cyclomatic"] == 14
        # Average computed across all files
        assert body["average_cyclomatic"] == (14 + 3) / 2

    def test_top_n_limits_results(
        self, client: TestClient, seeded_repository
    ) -> None:
        response = client.get(
            f"/api/v1/repositories/{seeded_repository.id}/complexity?top_n=1"
        )
        assert response.status_code == 200
        assert len(response.json()["top_files"]) == 1


class TestDeadCode:
    def test_lists_unused_symbols(
        self, client: TestClient, seeded_repository
    ) -> None:
        response = client.get(
            f"/api/v1/repositories/{seeded_repository.id}/dead-code"
        )
        assert response.status_code == 200
        body = response.json()
        names = {it["symbol_name"] for it in body["items"]}
        assert "orphan" in names
        assert "hello" not in names  # used, so not in the report
        assert body["summary"]["function"] == 1
        assert body["summary"]["total"] == 1


class TestReadOnlyInsightsRequireReadyStatus:
    def test_pending_repository_returns_409(
        self, client: TestClient
    ) -> None:
        # Submit a repo via the API; status is left at PENDING (no worker).
        created = client.post(
            "/api/v1/repositories",
            json={"url": "https://github.com/octocat/spoon-knife"},
        )
        repo_id = created.json()["repository_id"]
        response = client.get(f"/api/v1/repositories/{repo_id}/dependencies")
        assert response.status_code == 409
        assert response.json()["error"] == "analysis_not_ready"
