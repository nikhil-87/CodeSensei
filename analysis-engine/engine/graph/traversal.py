"""Reverse BFS for impact analysis."""
from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from engine.results import DependencyEdge


def reverse_bfs(
    edges: Iterable[DependencyEdge],
    start: str,
    *,
    max_depth: int = 5,
) -> list[tuple[str, int]]:
    """Return every node that *transitively depends on* ``start``.

    Output is a list of ``(path, depth)`` ordered by BFS layer.
    """
    inbound: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        inbound[edge.to_path].append(edge.from_path)

    visited: dict[str, int] = {start: 0}
    queue: deque[str] = deque([start])
    while queue:
        node = queue.popleft()
        depth = visited[node]
        if depth >= max_depth:
            continue
        for parent in inbound.get(node, ()):
            if parent in visited:
                continue
            visited[parent] = depth + 1
            queue.append(parent)

    out = [(p, d) for p, d in visited.items() if p != start]
    out.sort(key=lambda x: (x[1], x[0]))
    return out
