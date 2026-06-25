# Frontend Pages & Components

## Pages (`pages/`)

| Page | Purpose | Hooks / APIs |
| --- | --- | --- |
| `LoginPage` | GitHub OAuth or dev login | `useMe`, `useDevLogin` |
| `RepositoryListPage` | Owned repos grid + "Add repository" dialog | `useRepositories`, `useCreateRepository` |
| `RepositoryDashboardPage` | Status, metrics cards, analysis progress, delete/star/visibility | `useRepository`, `useAnalysisProgress`, `useTriggerAnalysis`, `useDeleteRepository`, `useSetVisibility` |
| `DependencyGraphPage` | Interactive graph + node inspector | `useDependencyGraph`, `useComplexity`, graphModel utils |
| `ComplexityPage` | Complexity bar chart + detail table | `useComplexity` |
| `DeadCodePage` | Unused-symbol table | `useDeadCode` |
| `ArchitecturePage` | Mermaid layers + drill-down inspector | `useArchitecture`, `useDependencyGraph` |
| `ImpactAnalysisPage` | File → blast-radius + criticality | `useImpact` |
| `AIAssistantPage` | Wraps `ChatPanel` behind an analysis gate | `ChatPanel` |
| `DiscoverPage` | Public discovery hub — one card per repository (`(url, branch)` group); search/sort/paginate | `useDiscover`, `useDebouncedValue` |
| `RepositoryAnalysesPage` | Repository overview / analysis-history (route `/discover/r?u=&b=`): header + an `Analysis #N` card per public analysis, analyst linked, freshness pill | `useDiscoverRepository` |
| `ProfilePage` | Public profile + their public repos | `useProfile`, `useProfileRepositories` |
| `StarredPage` | Repos the user starred | `useStarredRepositories` |
| `NotFoundPage` | 404 | — |

## Component groups (`components/`)

### `layout/` — `AppShell`, `Sidebar`, `Topbar`
Three-zone shell; responsive sidebar/drawer; sticky topbar with theme + user menu.

### `graph/` — `CytoscapeGraph`, `GraphToolbar`, `NodeInspector`
- `CytoscapeGraph`: renders nodes/edges; dagre + cose-bilkent layouts; directional
  relationship highlighting (selected / depends-on-this / this-depends-on); hover emphasis;
  on-canvas zoom/fit/fit-to-selection controls + legend; auto-fit after layout settles.
- `GraphToolbar`: view level, language filters, hide-isolated, cycles-only, focus mode +
  depth (1/2/3/All), layout picker, search/jump, reset.
- `NodeInspector`: rich panel — identity, impact analysis (criticality meter), code
  structure, usage (depends-on / depended-on-by), repository context, and AI action
  buttons that tag the file and route to chat.

### `ai-chat/` — `ChatPanel`, `SessionPickerModal`
- `ChatPanel`: session rail (desktop side / mobile drawer), transcript with numbered
  citations, composer pinned above the keyboard, attach-context chips, streaming + abort.
- `SessionPickerModal`: "Ask AI about this file" launcher — new or existing session, tags
  the file, preserves the starter prompt.

### `metrics/` — `ComplexityChart`, `LanguageChart`
Recharts. `ComplexityChart` is vertical bars on desktop, horizontal bars on mobile
(`useMediaQuery`) so labels stay readable.

### `architecture/` — `MermaidDiagram`
Renders the backend-generated Mermaid string with dark-mode theming.

### `repository/` — `RepositoryCard`, `DiscoverRepositoryCard`, `RepositoryAddDialog`, `StarButton`
- `RepositoryCard`: fully responsive, never clipped — `min-w-0`, truncation + tooltips,
  `shrink-0` badges/actions; shows a `Refresh recommended` chip when the analysis is stale.
- `DiscoverRepositoryCard`: repository-centric card for Discover — shows analyses count +
  total stars; links to the repository overview (`/discover/r`).
- `RepositoryAddDialog`: on a duplicate submit (`409 repository_already_exists`) switches to
  a Refresh / Open existing / Cancel choice instead of creating a duplicate.
- `StarButton`: optimistic toggle reconciled with the server's returned count.

### `analysis/` — `AnalysisGate`, `AnalysisProgress`, `AnalysisFreshnessBanner`
- `AnalysisGate`: returns a blocker (loading/error/not-ready/stale) or `null` (ready) to
  guard insight pages and chat.
- `AnalysisFreshnessBanner`: warns when stored version stamps trail current constants.

### `common/` — primitives
`Button` (variants/sizes/loading/icons), `Card` (+ `contentClassName` so flex-height
children like chat work), `Skeleton` set, `Pagination` (numbered ≥sm, chevrons on mobile),
`Spinner`, `StatusBadge`, `EmptyState`, `ErrorState`, `Logo`, `ThemeToggle`.

### `auth/` — `RequireAuth`
Guards protected routes; spinner while auth resolves, redirect to `/login` otherwise.

### `dead-code/` — `DeadCodeTable`
Sortable, horizontally scrollable table of unused symbols.

## `lib/graphModel.ts` (graph math, pure + testable)
- `buildAdjacency(edges)` → `{out, in}` maps.
- `reachable(start, adj, dir, maxDepth)` → BFS set (focus mode depth).
- `chainDepth(...)` → longest dependency chain (cycle-safe).
- `computeImpact(fileId, adj, totalFiles)` → `{impactScope, dependencyReach, impactDepth,
  dependencyDepth, criticality 0–100, criticalityLabel}`.
- `computeClusters(files, expanded)` / `aggregateEdges(...)` → folder folding for the graph.
- `classifyLayer` / `layerLabel` / `colorForLanguage` → presentation helpers.
