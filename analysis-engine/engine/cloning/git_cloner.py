"""Safe, bounded git clone.

Defence-in-depth: the URL is *also* validated by the API layer (see
``backend/app/core/security.py``). The engine re-validates the basic
shape because it might be called from a CLI or test that didn't go
through the backend.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import structlog

from engine.exceptions import CloneError, RepositoryTooLargeError
from engine import _defaults

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class CloneOptions:
    """Tunable knobs for the clone phase."""

    workspace_root: Path
    branch: str | None = None
    depth: int = _defaults.CLONE_DEPTH
    timeout_seconds: int = _defaults.CLONE_TIMEOUT_SECONDS
    max_size_mb: int = _defaults.API_MAX_REPO_SIZE_MB


class GitCloner:
    """Thin wrapper over ``git clone`` with timeout + size enforcement.

    We use the ``git`` CLI rather than libgit2/dulwich/GitPython for the
    actual fetch because the CLI is the only implementation that handles
    every protocol quirk in real-world repositories. GitPython is only
    used in tests (it's not in this module).
    """

    def __init__(self, options: CloneOptions) -> None:
        self._options = options

    def clone(self, github_url: str) -> Path:
        """Clone ``github_url`` into ``workspace_root``. Returns the path.

        The destination directory is named from the URL path so that
        re-cloning the same repository overwrites cleanly.
        """
        self._ensure_safe_url(github_url)

        target = self._options.workspace_root / self._slug(github_url)
        if target.exists():
            shutil.rmtree(target, ignore_errors=False)
        target.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "git",
            "clone",
            "--depth",
            str(self._options.depth),
            "--single-branch",
        ]
        if self._options.branch:
            cmd += ["--branch", self._options.branch]
        cmd += [github_url, str(target)]

        logger.info("git_clone_start", url=github_url, branch=self._options.branch)
        started = time.monotonic()
        try:
            proc = subprocess.run(  # noqa: S603 — args are vetted, shell=False
                cmd,
                capture_output=True,
                text=True,
                timeout=self._options.timeout_seconds,
                check=False,
                env=self._scrubbed_env(),
            )
        except subprocess.TimeoutExpired as exc:
            raise CloneError(
                f"git clone timed out after {self._options.timeout_seconds}s"
            ) from exc
        except FileNotFoundError as exc:  # pragma: no cover — git missing
            raise CloneError("git executable not found on PATH") from exc

        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip().splitlines()[-3:]
            raise CloneError(
                "git clone failed: " + (" | ".join(stderr) or "no stderr")
            )

        elapsed = time.monotonic() - started
        size_bytes = self._directory_size(target)
        size_mb = size_bytes / (1024 * 1024)

        logger.info(
            "git_clone_done",
            url=github_url,
            elapsed_seconds=round(elapsed, 2),
            size_mb=round(size_mb, 2),
        )

        if size_mb > self._options.max_size_mb:
            shutil.rmtree(target, ignore_errors=True)
            raise RepositoryTooLargeError(
                f"Repository is {size_mb:.0f} MB; limit is "
                f"{self._options.max_size_mb} MB"
            )

        return target

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------
    @staticmethod
    def head_commit(target: Path) -> str | None:
        """Return the full SHA of ``HEAD`` in a cloned tree, or ``None``.

        Best-effort provenance: a failure here must never fail an analysis,
        so any error degrades to ``None`` (the analysis is simply stored
        without a commit stamp).
        """
        try:
            proc = subprocess.run(  # noqa: S603 — fixed args, shell=False
                ["git", "-C", str(target), "rev-parse", "HEAD"],  # noqa: S607
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
        if proc.returncode != 0:
            return None
        sha = (proc.stdout or "").strip()
        return sha or None

    @staticmethod
    def _ensure_safe_url(url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme not in {"https", "http"}:
            raise CloneError(f"Refusing to clone scheme={parsed.scheme!r}")
        if parsed.username or parsed.password:
            raise CloneError("Refusing to clone URLs with embedded credentials")
        if not parsed.netloc or "@" in parsed.netloc:
            raise CloneError(f"Refusing malformed URL: {url}")

    @staticmethod
    def _slug(url: str) -> str:
        path = urlparse(url).path.strip("/")
        if path.endswith(".git"):
            path = path[:-4]
        owner, _, name = path.partition("/")
        return f"{owner}__{name}"

    @staticmethod
    def _scrubbed_env() -> dict[str, str]:
        """Minimal env so credential helpers / proxies don't leak in.

        We strip everything starting with ``GIT_`` except a small allow-list
        used by the platform's CI image.
        """
        allow = {"GIT_TERMINAL_PROMPT": "0"}
        env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
        env.update(allow)
        return env

    @staticmethod
    def _directory_size(path: Path) -> int:
        total = 0
        for root, _dirs, files in os.walk(path):
            for f in files:
                fp = Path(root) / f
                try:
                    total += fp.stat().st_size
                except OSError:
                    continue
        return total
