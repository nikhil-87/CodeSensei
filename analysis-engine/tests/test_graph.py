"""Graph builder + cycle detection."""
from __future__ import annotations

from engine.graph.builder import GraphBuilder
from engine.graph.cycles import detect_cycles
from engine.graph.traversal import reverse_bfs
from engine.results import (
    DependencyEdge,
    FileAnalysis,
    FileMetrics,
    Import,
)


def _file(path: str, *imports: Import) -> FileAnalysis:
    return FileAnalysis(
        path=path,
        language="python",
        size_bytes=0,
        line_count=0,
        sha256="",
        symbols=(),
        imports=tuple(imports),
        metrics=FileMetrics(0, 0, 0, 0, 0),
        parser="test",
    )


class TestGraphBuilder:
    def test_resolves_relative_python_imports(self) -> None:
        files = [
            _file("pkg/__init__.py"),
            _file("pkg/util.py"),
            _file(
                "pkg/main.py",
                Import(module=".util", line=1, is_relative=True),
            ),
        ]
        edges = GraphBuilder(files).build()
        assert any(e.from_path == "pkg/main.py" and e.to_path == "pkg/util.py" for e in edges)

    def test_resolves_dotted_python_module(self) -> None:
        files = [
            _file("a/b/c.py"),
            _file("user.py", Import(module="a.b.c", line=1)),
        ]
        edges = GraphBuilder(files).build()
        assert edges
        assert edges[0].to_path == "a/b/c.py"

    def test_resolves_js_relative_with_extension_inference(self) -> None:
        files = [
            FileAnalysis(
                path="src/utils.ts",
                language="typescript",
                size_bytes=0, line_count=0, sha256="",
                symbols=(), imports=(),
                metrics=FileMetrics(0, 0, 0, 0, 0), parser="test",
            ),
            FileAnalysis(
                path="src/main.ts",
                language="typescript",
                size_bytes=0, line_count=0, sha256="",
                symbols=(),
                imports=(Import(module="./utils", line=1, is_relative=True),),
                metrics=FileMetrics(0, 0, 0, 0, 0), parser="test",
            ),
        ]
        edges = GraphBuilder(files).build()
        assert edges
        assert edges[0].to_path == "src/utils.ts"

    def test_drops_external_imports(self) -> None:
        files = [
            _file("a.py", Import(module="numpy", line=1)),
        ]
        assert GraphBuilder(files).build() == ()


class TestCycleDetection:
    def test_detects_simple_cycle(self) -> None:
        edges = [
            DependencyEdge(from_path="a.py", to_path="b.py", kind="import"),
            DependencyEdge(from_path="b.py", to_path="a.py", kind="import"),
        ]
        cycles = detect_cycles(["a.py", "b.py"], edges)
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a.py", "b.py"}

    def test_detects_three_node_cycle(self) -> None:
        edges = [
            DependencyEdge("a", "b", "import"),
            DependencyEdge("b", "c", "import"),
            DependencyEdge("c", "a", "import"),
        ]
        cycles = detect_cycles(["a", "b", "c"], edges)
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b", "c"}

    def test_no_cycle_in_dag(self) -> None:
        edges = [
            DependencyEdge("a", "b", "import"),
            DependencyEdge("b", "c", "import"),
        ]
        assert detect_cycles(["a", "b", "c"], edges) == ()


class TestReverseBfs:
    def test_returns_transitive_dependents(self) -> None:
        edges = [
            DependencyEdge("a", "core", "import"),
            DependencyEdge("b", "a", "import"),
            DependencyEdge("c", "b", "import"),
        ]
        impacted = reverse_bfs(edges, "core")
        names = {p for p, _ in impacted}
        assert names == {"a", "b", "c"}
        depth_for = dict(impacted)
        assert depth_for["a"] == 1
        assert depth_for["b"] == 2
        assert depth_for["c"] == 3

    def test_respects_max_depth(self) -> None:
        edges = [
            DependencyEdge("a", "core", "import"),
            DependencyEdge("b", "a", "import"),
            DependencyEdge("c", "b", "import"),
        ]
        impacted = reverse_bfs(edges, "core", max_depth=2)
        names = {p for p, _ in impacted}
        assert names == {"a", "b"}
