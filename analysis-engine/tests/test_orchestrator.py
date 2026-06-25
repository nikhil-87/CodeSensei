"""End-to-end orchestrator + walker test using a synthetic Python repo."""
from __future__ import annotations

from pathlib import Path

from engine.orchestrator import AnalysisOptions, AnalysisOrchestrator


def test_full_pipeline_on_synthetic_python_repo(make_repo, tmp_path: Path) -> None:
    repo = make_repo(
        {
            "pkg/__init__.py": "",
            "pkg/util.py": (
                "def helper(x):\n"
                "    if x > 0:\n"
                "        return x\n"
                "    return -1\n"
            ),
            "pkg/main.py": (
                "from . import util\n"
                "from .util import helper\n"
                "def run():\n"
                "    return helper(1)\n"
            ),
            "scripts/orphan.py": (
                "def something_unused():\n"
                "    return 42\n"
            ),
            "tests/test_main.py": (
                "from pkg.main import run\n"
                "def test_run():\n"
                "    assert run() == 1\n"
            ),
            ".gitignore": "build/\n",
            "build/leftover.py": "x = 1\n",
        }
    )

    options = AnalysisOptions(workspace_root=tmp_path / "ws")
    orchestrator = AnalysisOrchestrator(options)
    result = orchestrator.run_on_path(repo)

    paths = {f.path for f in result.files}
    assert "pkg/util.py" in paths
    assert "pkg/main.py" in paths
    # gitignored file must be excluded
    assert "build/leftover.py" not in paths

    # Dependency graph: main.py → util.py (resolved relative)
    edges = {(e.from_path, e.to_path) for e in result.dependencies}
    assert ("pkg/main.py", "pkg/util.py") in edges

    # Architecture report has at least one layer
    assert result.architecture is not None
    assert len(result.architecture.layers) >= 1

    # Languages aggregated
    assert result.languages.get("python", 0) >= 3

    # Total LOC is positive
    assert result.total_lines > 0


def test_pipeline_yields_dead_code_for_unimported_orphan(make_repo, tmp_path: Path) -> None:
    repo = make_repo(
        {
            "lib/used.py": "def shared():\n    return 1\n",
            "lib/main.py": "from . import used\nused.shared()\n",
            "lib/orphan.py": "def never_called():\n    return 7\n",
        }
    )
    result = AnalysisOrchestrator(
        AnalysisOptions(workspace_root=tmp_path / "ws")
    ).run_on_path(repo)

    findings = {(f.file_path, f.symbol_name) for f in result.dead_code}
    assert ("lib/orphan.py", "never_called") in findings
