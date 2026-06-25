"""Strongly-connected component (cycle) detection — Tarjan's algorithm.

Iterative implementation so we never blow the recursion limit on huge
graphs. Returns components of size > 1 (or self-loops), each as a tuple
of node identifiers in insertion order.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from engine.results import DependencyEdge


def detect_cycles(
    nodes: Iterable[str], edges: Iterable[DependencyEdge]
) -> tuple[tuple[str, ...], ...]:
    """Return every non-trivial SCC in the dependency graph."""
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[edge.from_path].append(edge.to_path)

    node_list = list(dict.fromkeys(nodes))  # preserve insertion order
    index_of: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    sccs: list[tuple[str, ...]] = []
    counter = 0

    # Iterative DFS; each frame is (node, iterator over neighbours).
    for root in node_list:
        if root in index_of:
            continue
        work: list[tuple[str, list[str], int]] = [(root, adjacency.get(root, []), 0)]
        index_of[root] = counter
        lowlink[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)

        while work:
            node, neighbours, pos = work[-1]
            if pos < len(neighbours):
                work[-1] = (node, neighbours, pos + 1)
                child = neighbours[pos]
                if child not in index_of:
                    index_of[child] = counter
                    lowlink[child] = counter
                    counter += 1
                    stack.append(child)
                    on_stack.add(child)
                    work.append((child, adjacency.get(child, []), 0))
                elif child in on_stack:
                    lowlink[node] = min(lowlink[node], index_of[child])
            else:
                # Backtrack: pop frame and propagate lowlink upward.
                work.pop()
                if lowlink[node] == index_of[node]:
                    component: list[str] = []
                    while True:
                        popped = stack.pop()
                        on_stack.discard(popped)
                        component.append(popped)
                        if popped == node:
                            break
                    if len(component) > 1 or _is_self_loop(node, adjacency):
                        sccs.append(tuple(reversed(component)))
                if work:
                    parent_node = work[-1][0]
                    lowlink[parent_node] = min(lowlink[parent_node], lowlink[node])

    return tuple(sccs)


def _is_self_loop(node: str, adjacency: dict[str, list[str]]) -> bool:
    return node in adjacency.get(node, ())
