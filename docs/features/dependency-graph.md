# Feature: Dependency Graph & Node Intelligence

## What it does
An interactive visualization of how files in a repository depend on each other, plus a rich
"code intelligence" inspector for any selected node, and one-click "Ask AI about this node"
actions that carry the file into a chat session.

## Why it exists
Reading import statements across hundreds of files doesn't scale. The graph makes structure,
coupling, cycles, and blast-radius visible, and the inspector turns a node into an
explainable, askable unit.

## User workflow
1. Open `…/graph`. The graph auto-fits to the viewport.
2. Cluster/expand folders; filter by language; toggle cycles-only / hide-isolated.
3. Click a node → the inspector shows identity, impact, code structure, usage, and layer.
4. Selecting a node highlights its relationships directionally:
   - **blue** = files that depend on this (incoming),
   - **amber** = files this depends on (outgoing),
   - unrelated nodes dim but stay visible.
5. Enter **focus mode** to isolate a node's reachable set with a depth limit (1/2/3/All).
6. Click an AI action ("Explain this file", "Find potential risks", "Show impact of
   changes", …) → the file is tagged and a chat session opens with the prompt pre-filled.

## Backend implementation
- **Route:** `GET /repositories/{id}/dependencies` → `DependencyService.get_graph` →
  `DependencyGraphResponse { nodes, edges, cycles }`.
- Nodes come from `source_files` (+ degrees), edges from `dependencies`, cycles from the
  engine's cycle detector.

## Frontend implementation
- **Page:** `DependencyGraphPage` orchestrates state (level, expansion, filters, selection,
  focus + depth) and derives a render model with `lib/graphModel.ts`.
- **`CytoscapeGraph`:** dagre/cose-bilkent layouts; directional highlight classes;
  hover emphasis; on-canvas zoom / fit / fit-to-selection controls + a legend; auto-fit
  after the layout settles (fixes a zoom-stuck-off-screen bug). Overlays are excluded from
  the "fill host" CSS via `data-graph-overlay` so they don't cover the canvas.
- **`NodeInspector`:** sections for Impact analysis (`computeImpact` → criticality meter +
  scope/reach/depth), Code structure (LOC, functions, classes, cyclomatic, cognitive),
  Usage (clickable depends-on / depended-on-by with colored dots), Repository context
  (layer/module), and AI actions.
- **`GraphToolbar`:** view level, language filters, cycles-only, hide-isolated, focus +
  depth, layout, search/jump, reset. Keyboard: `Esc` clears, `f` toggles focus.

## "Ask AI about this node" flow
The inspector calls `nodeContextStore.attachFile(repoId, {path, language})` +
`setPendingPrompt(prompt)`, opens `SessionPickerModal`, and navigates to
`/chat?session=<id>`. `ChatPanel` consumes the pending prompt and sends it with the file as
`attached_paths`, which RAG gives guaranteed retrieval slots. The file shows as a Context
chip in the composer. See [ai-chat.md](ai-chat.md).

## Tables involved
- `source_files`, `dependencies` (graph); `metrics` (inspector complexity).

## APIs
`GET /repositories/{id}/dependencies`; chat APIs for the AI actions.

## Edge cases handled
- **Empty/sparse graphs** — friendly empty state.
- **Huge graphs** — clustering, language filters, focus + depth keep it legible.
- **Layout off-screen** — deferred `cy.fit()` after layout settles.
- **Overlay covering canvas** — `data-graph-overlay` excluded from the fill rule.
- **Mobile** — controls remain touch-accessible; no horizontal overflow.

## Security considerations
- Read gated by `verify_repository_access`. AI actions inherit chat ownership/repo checks.

## Honest limitation
Edges are **file-level imports** (the analyzer emits `import` edges, not per-function
`call` edges). The inspector's "usage" is therefore import/file granularity, not a true
call graph. The schema and UI are ready for richer edges when the analyzer produces them.
See [../decisions/0008-dependency-graph.md](../decisions/0008-dependency-graph.md).

## Future improvements
- Symbol/call-level edges and a function-level inspector.
- Minimap for very large graphs.
- Saved views / shareable focus links (partially supported via `?focus=` deep links).
