"""Unit tests for app.core.security — URL & branch validation, path guards."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.core.exceptions import (
    InvalidRepositoryURLError,
    PathTraversalError,
)
from app.core.security import (
    hash_text,
    repo_slug,
    safe_join,
    validate_branch_name,
    validate_github_url,
    workspace_path,
)


# --------------------------------------------------------------------------- URL
class TestValidateGithubUrl:
    @pytest.mark.parametrize(
        "url",
        [
            "https://github.com/octocat/Hello-World",
            "https://github.com/octocat/Hello-World.git",
            "https://github.com/octocat/Hello-World/",
            "https://www.github.com/octocat/Hello-World",
        ],
    )
    def test_accepts_canonical_urls(self, url: str) -> None:
        out = validate_github_url(url)
        assert out == "https://github.com/octocat/Hello-World"

    @pytest.mark.parametrize(
        "url",
        [
            "http://github.com/x/y",  # http not allowed
            "https://gitlab.com/x/y",  # wrong host
            "https://github.com/onlyone",  # missing repo
            "https://github.com/",
            "https://github.com/a/b?token=abc",  # query disallowed
            "https://user:pass@github.com/a/b",  # credentials
            "git@github.com:a/b.git",  # ssh form
            "https://github.com:8080/a/b",  # custom port
            "ftp://github.com/a/b",
            "",
            "not-a-url",
        ],
    )
    def test_rejects_invalid_urls(self, url: str) -> None:
        with pytest.raises(InvalidRepositoryURLError):
            validate_github_url(url)


# --------------------------------------------------------------------------- Branch
class TestValidateBranchName:
    @pytest.mark.parametrize(
        "branch", ["main", "develop", "feature/x-1", "release-1.2.3", None]
    )
    def test_valid_branches(self, branch: str | None) -> None:
        assert validate_branch_name(branch) == branch

    @pytest.mark.parametrize(
        "branch", ["..", "/main", "main/", "feat..ure", "feat~1", "with space", "x" * 300]
    )
    def test_invalid_branches(self, branch: str) -> None:
        with pytest.raises(InvalidRepositoryURLError):
            validate_branch_name(branch)


# --------------------------------------------------------------------------- Path-traversal
class TestSafeJoin:
    def test_allows_subpaths(self, tmp_path: Path) -> None:
        out = safe_join(tmp_path, "sub/dir/file.txt")
        assert str(out).startswith(str(tmp_path))

    @pytest.mark.parametrize(
        "evil",
        ["../etc/passwd", "..\\..\\windows\\system32", "/abs/path", "sub/../../../etc"],
    )
    def test_rejects_traversal(self, tmp_path: Path, evil: str) -> None:
        with pytest.raises(PathTraversalError):
            safe_join(tmp_path, evil)


# --------------------------------------------------------------------------- Hash / slug
class TestHelpers:
    def test_hash_is_stable(self) -> None:
        assert hash_text("abc") == hash_text("abc")
        assert len(hash_text("abc")) == 64

    def test_repo_slug(self) -> None:
        assert (
            repo_slug("https://github.com/octocat/Hello-World")
            == "octocat__Hello-World"
        )

    def test_workspace_path_is_safe(self, tmp_path: Path) -> None:
        path = workspace_path(tmp_path, "https://github.com/octocat/Hello-World")
        assert path.parent == tmp_path
        assert path.name == "octocat__Hello-World"
