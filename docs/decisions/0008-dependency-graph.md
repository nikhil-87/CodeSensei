# ADR-0008: File-level import dependency graph

**Status:** Accepted (with a known limitation)

## Context
A dependency graph is central to the product. The ideal is a symbol/call-level graph
("function A calls function B"), but resolving calls accurately across 9+ languages
(dynamic dispatch, duck typing, reflection) is hard and brittle.

## Decision
Build a **file-level dependency graph from import statements**. Each parser emits imports;
the graph builder resolves them to concrete files (relative, module, and fuzzy resolution).
The schema (`dependencies.kind`) supports `import|inheritance|call|instantiation|reference`,
but the analyzers currently emit **file-level `import` edges**.

## Alternatives considered
- **Full symbol/call graph** — most valuable, but accurate cross-language call resolution is
  a large, error-prone effort; false edges would mislead users.
- **No graph (text search only)** — loses the structural insight that's a headline feature.

## Consequences
- (+) Robust and accurate across many languages; cycles and module structure are real.
- (+) Powers impact/criticality at file granularity reliably.
- (−) Not a true call graph — the inspector's "usage" is import/file level. This is
  **documented honestly** in the UI and [../features/dependency-graph.md](../features/dependency-graph.md).
- (+) The schema + frontend are ready for richer edges when analyzers produce them
  (incremental upgrade, no redesign).
