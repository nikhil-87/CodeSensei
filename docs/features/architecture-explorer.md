# Feature: Architecture Explorer

## What it does
Groups a repository's files into architectural **layers** (controllers, services,
repositories, models, infrastructure, UI, tests, other) and renders a **Mermaid** diagram
of how layers relate, with drill-down into folders/files using the same node inspector as
the dependency graph.

## Why it exists
A dependency graph shows *files*; the architecture view shows *intent* — the high-level
shape of the system. It helps a reviewer judge layering discipline at a glance.

## User workflow
1. Open `…/architecture`.
2. See the layer diagram + summary.
3. Drill into a folder; inspect files; jump to the graph or ask AI.

## Backend implementation
- **Route:** `GET /repositories/{id}/architecture` → `ArchitectureService.report` →
  `ArchitectureReport { layers, components, mermaid_diagram, summary }`.
- Layer classification mirrors `lib/graphModel.classifyLayer` on the frontend (path-hint
  based) so both surfaces agree.

## Frontend implementation
- **Page:** `ArchitecturePage` renders `MermaidDiagram` (dark-mode aware) + a drill-down
  using `NodeInspector`.
- Responsive: `max-w-[1700px]`, graph/inspector heights `h-[480px] lg:h-[640px]`.

## Tables involved
- `source_files` (+ paths for layer classification), `dependencies` (cross-layer edges).

## APIs
`GET /repositories/{id}/architecture`.

## Edge cases handled
- Repos that don't match common layer hints fall into "other".
- Mermaid render errors are contained to the diagram component.

## Security considerations
- Read gated by `verify_repository_access`.

## Future improvements
- Layering-violation detection (e.g. model importing a controller).
- Configurable layer rules per repo.
