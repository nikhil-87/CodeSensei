"""Shared fixtures — synthetic repository builder."""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pytest


@pytest.fixture
def make_repo(tmp_path: Path):
    """Factory: write a dict of {relative_path: contents} into a temp dir."""

    def _make(files: Mapping[str, str], *, name: str = "repo") -> Path:
        root = tmp_path / name
        root.mkdir(parents=True, exist_ok=True)
        for rel, contents in files.items():
            target = root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents, encoding="utf-8")
        return root

    return _make
