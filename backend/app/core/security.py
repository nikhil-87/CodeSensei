"""Security primitives — URL validation, path-traversal guards, hashing.

This module is intentionally narrow. We do NOT implement authentication here
(see ADR-0010 — fronted by reverse proxy).
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from urllib.parse import urlparse

from app.core.exceptions import InvalidRepositoryURLError, PathTraversalError

# Public GitHub repository URL pattern (HTTPS only — no SSH, no scp-style).
# We deliberately reject query strings, fragments, ports, and userinfo.
_GITHUB_HOST = "github.com"
_REPO_PATH_RE = re.compile(r"^/[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+(?:\.git)?/?$")
_VALID_BRANCH_RE = re.compile(r"^[A-Za-z0-9_./\-]{1,255}$")


def validate_github_url(url: str) -> str:
    """Validate a public GitHub repository URL.

    Returns the canonical form (https, no trailing slash, no .git suffix).
    Raises InvalidRepositoryURLError on any rejection.
    """
    if not isinstance(url, str) or not url.strip():
        raise InvalidRepositoryURLError("URL is empty")

    url = url.strip()

    try:
        parsed = urlparse(url)
    except ValueError as exc:
        raise InvalidRepositoryURLError(f"Cannot parse URL: {exc}") from exc

    if parsed.scheme != "https":
        raise InvalidRepositoryURLError("Only https:// URLs are accepted")
    host = (parsed.hostname or "").removeprefix("www.")
    if host != _GITHUB_HOST:
        raise InvalidRepositoryURLError(
            f"Only repositories on {_GITHUB_HOST} are supported"
        )
    if parsed.port not in (None, 443):
        raise InvalidRepositoryURLError("Custom ports are not allowed")
    if parsed.username or parsed.password:
        raise InvalidRepositoryURLError("URL must not contain credentials")
    if parsed.query or parsed.fragment:
        raise InvalidRepositoryURLError("URL must not contain query or fragment")
    if not _REPO_PATH_RE.match(parsed.path):
        raise InvalidRepositoryURLError("URL path must be /<owner>/<repo>")

    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    return f"https://{_GITHUB_HOST}{path}"


def validate_branch_name(branch: str | None) -> str | None:
    """Validate a Git branch name (or None for default branch)."""
    if branch is None or branch == "":
        return None
    branch = branch.strip()
    if not _VALID_BRANCH_RE.match(branch):
        raise InvalidRepositoryURLError(f"Invalid branch name: {branch!r}")
    if (
        branch.startswith("-")
        or branch.startswith("/")
        or branch.endswith("/")
        or ".." in branch
    ):
        raise InvalidRepositoryURLError(f"Invalid branch name: {branch!r}")
    return branch


def safe_join(root: str | Path, *parts: str) -> Path:
    """Join `parts` under `root`, rejecting any path that escapes `root`.

    Protects against path-traversal payloads like `../../etc/passwd` or
    absolute paths embedded in untrusted segments.

    Backslashes are rejected outright: they are path separators on Windows but
    ordinary characters on POSIX, so accepting them would make traversal
    detection platform-dependent. Rejecting them keeps the guard identical on
    every host the app runs on.
    """
    for part in parts:
        if "\\" in part:
            raise PathTraversalError(
                f"Path segment {part!r} contains an illegal backslash"
            )
    root_path = Path(root).resolve()
    candidate = root_path.joinpath(*parts).resolve()
    try:
        candidate.relative_to(root_path)
    except ValueError as exc:
        raise PathTraversalError(
            f"Path {candidate} escapes root {root_path}"
        ) from exc
    return candidate


def hash_text(text: str) -> str:
    """Stable SHA-256 hex digest. Used for cache keys."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def repo_slug(github_url: str) -> str:
    """Filesystem-safe slug for a repository URL."""
    canonical = validate_github_url(github_url)
    parsed = urlparse(canonical)
    owner, name = parsed.path.strip("/").split("/", 1)
    return f"{owner}__{name}"


def workspace_path(root: str | Path, github_url: str) -> Path:
    """Compute the on-disk workspace directory for a repository."""
    return safe_join(root, repo_slug(github_url))


def ensure_within_size_limit(size_bytes: int, limit_mb: int) -> None:
    """Reject if `size_bytes` exceeds `limit_mb`."""
    if size_bytes > limit_mb * 1024 * 1024:
        raise InvalidRepositoryURLError(
            f"Repository size {size_bytes} bytes exceeds {limit_mb} MB limit"
        )


def umask_for_clones() -> int:
    """Process umask we use when creating workspace directories (group-read only)."""
    return 0o027


def apply_workspace_umask() -> None:
    os.umask(umask_for_clones())
