"""Cross-stack contract tests.

These tests guard the API surface that the frontend SPA consumes. They
inspect the FastAPI app's generated OpenAPI document and assert that every
HTTP method/path the frontend touches actually exists, and that the response
schemas have the field names the TypeScript layer expects.

The frontend's TypeScript types live at
``frontend/src/types/api.ts``; this file mirrors *those* expectations so a
backwards-incompatible backend change fails CI before the SPA does.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# Make the backend importable without installing it.
ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from app.core.config import Settings  # noqa: E402
from app.main import create_app  # noqa: E402


@pytest.fixture(scope="module")
def openapi() -> dict:
    settings = Settings(
        app_env="test",
        app_secret_key="contract-test-secret-must-be-at-least-32-characters",
        postgres_password="x",
    )
    app = create_app(settings)
    return app.openapi()


# ---------------------------------------------------------------------------
# Endpoint surface — every entry the frontend api client hits
# (frontend/src/api/*.ts) must exist in the OpenAPI document.
# ---------------------------------------------------------------------------
ENDPOINT_CONTRACT: list[tuple[str, str]] = [
    # repositories
    ("get", "/api/v1/repositories"),
    ("post", "/api/v1/repositories"),
    ("get", "/api/v1/repositories/{repository_id}"),
    ("delete", "/api/v1/repositories/{repository_id}"),
    # analysis jobs
    ("post", "/api/v1/repositories/{repository_id}/analyze"),
    ("get", "/api/v1/repositories/{repository_id}/jobs"),
    ("get", "/api/v1/repositories/{repository_id}/jobs/latest"),
    ("get", "/api/v1/repositories/{repository_id}/events"),
    # insights
    ("get", "/api/v1/repositories/{repository_id}/dependencies"),
    ("get", "/api/v1/repositories/{repository_id}/complexity"),
    ("get", "/api/v1/repositories/{repository_id}/dead-code"),
    ("get", "/api/v1/repositories/{repository_id}/architecture"),
    ("post", "/api/v1/repositories/{repository_id}/impact"),
    # health / observability
    ("get", "/healthz"),
    ("get", "/readyz"),
]


@pytest.mark.parametrize("method,path", ENDPOINT_CONTRACT)
def test_endpoint_present_in_openapi(
    openapi: dict, method: str, path: str
) -> None:
    paths = openapi["paths"]
    assert path in paths, f"Endpoint {path} missing from OpenAPI"
    assert method in paths[path], (
        f"Method {method.upper()} not declared on {path}"
    )


# ---------------------------------------------------------------------------
# Schema field-name parity — guards renames
# ---------------------------------------------------------------------------
SCHEMA_CONTRACT: dict[str, set[str]] = {
    "RepositoryRead": {
        "id", "url", "branch", "default_branch", "name", "owner",
        "status", "analyzed_at", "file_count", "total_lines", "languages",
        "created_at", "updated_at",
    },
    "AnalysisJobRead": {
        "id", "repository_id", "status", "rq_job_id", "queued_at",
        "started_at", "completed_at", "progress", "progress_message",
    },
    "DependencyGraphResponse": {"repository_id", "nodes", "edges", "cycles"},
    "ComplexityRanking": {
        "repository_id", "top_files",
        "average_cyclomatic", "average_cognitive", "median_lines_of_code",
    },
    "DeadCodeReport": {"repository_id", "items", "summary"},
    "ArchitectureReport": {
        "repository_id", "layers", "components", "mermaid_diagram", "summary",
    },
}


@pytest.mark.parametrize("schema_name,expected_fields", list(SCHEMA_CONTRACT.items()))
def test_schema_has_expected_fields(
    openapi: dict, schema_name: str, expected_fields: set[str]
) -> None:
    schemas = openapi["components"]["schemas"]
    assert schema_name in schemas, f"Schema {schema_name} not in OpenAPI"
    actual_fields = set(schemas[schema_name].get("properties", {}).keys())
    missing = expected_fields - actual_fields
    assert not missing, (
        f"{schema_name} is missing fields the frontend depends on: {missing}"
    )


# ---------------------------------------------------------------------------
# Enum parity — keep status / kind enums in lock-step with TypeScript unions.
# ---------------------------------------------------------------------------
ENUM_CONTRACT: dict[str, set[str]] = {
    "RepositoryStatus": {"pending", "cloning", "analyzing", "ready", "failed"},
    "AnalysisJobStatus": {
        "queued", "running", "succeeded", "failed", "cancelled",
    },
    "DependencyKind": {
        "import", "inheritance", "call", "instantiation", "reference",
    },
    "SymbolKind": {
        "function", "method", "class", "interface", "struct", "enum",
        "variable", "constant", "type_alias", "module",
    },
}


@pytest.mark.parametrize("enum_name,expected", list(ENUM_CONTRACT.items()))
def test_enum_values_match_frontend(
    openapi: dict, enum_name: str, expected: set[str]
) -> None:
    schemas = openapi["components"]["schemas"]
    assert enum_name in schemas, f"Enum {enum_name} missing from OpenAPI"
    actual = set(schemas[enum_name]["enum"])
    assert actual == expected, (
        f"{enum_name} drifted: expected {expected}, got {actual}"
    )


# ---------------------------------------------------------------------------
# TypeScript snapshot \u2014 ensures the hand-curated frontend types include
# the same enum members.
# ---------------------------------------------------------------------------
def _ts_union_members(text: str, type_name: str) -> set[str]:
    pattern = re.compile(
        rf"export type {type_name}\s*=\s*([^;]+);", re.MULTILINE
    )
    match = pattern.search(text)
    assert match, f"Type {type_name} not declared in api.ts"
    return set(re.findall(r'"([a-z_]+)"', match.group(1)))


def test_frontend_repository_status_in_sync() -> None:
    api_ts = (ROOT / "frontend" / "src" / "types" / "api.ts").read_text(
        encoding="utf-8"
    )
    members = _ts_union_members(api_ts, "RepositoryStatus")
    # Frontend may omit transient values it never displays, but everything
    # listed there must be a real backend value.
    assert members.issubset(
        ENUM_CONTRACT["RepositoryStatus"]
    ), f"Frontend RepositoryStatus diverged: {members}"


def test_frontend_job_status_matches_backend() -> None:
    api_ts = (ROOT / "frontend" / "src" / "types" / "api.ts").read_text(
        encoding="utf-8"
    )
    members = _ts_union_members(api_ts, "AnalysisJobStatus")
    assert members == ENUM_CONTRACT["AnalysisJobStatus"]
