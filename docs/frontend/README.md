# Frontend Documentation

A **React 18 + Vite 5 + TypeScript (strict)** SPA, styled with **Tailwind 3**, state via
**Zustand 5**, data fetching via **TanStack Query 5**, routing via **react-router-dom 6**.
Graphs use **Cytoscape**, charts use **Recharts**, architecture diagrams use **Mermaid**.

| Doc | Covers |
| --- | --- |
| This file | Structure, routing, layout, responsive strategy, build/tooling |
| [state-and-data.md](state-and-data.md) | Zustand stores, TanStack Query hooks, API client, SSE |
| [pages-and-components.md](pages-and-components.md) | Every page + key component groups |
| [../features/dependency-graph.md](../features/dependency-graph.md) | The graph UI in depth |
| [../features/ai-chat.md](../features/ai-chat.md) | The chat UI in depth |

## Directory map (`frontend/src/`)

```
src/
├── pages/         # one component per route
├── components/    # feature-grouped: layout, graph, ai-chat, metrics, architecture,
│                  #   repository, analysis, common, auth, dead-code
├── hooks/         # TanStack Query hooks + useMediaQuery, useDebouncedValue
├── store/         # Zustand: uiStore, themeStore, nodeContextStore
├── api/           # typed API client modules (one per backend resource)
├── lib/           # api.ts, sse.ts, graphModel.ts, format.ts, queryClient.ts, config.ts
├── routes/        # router.tsx (route table + guards)
├── types/         # shared API TypeScript types
├── App.tsx        # QueryClientProvider + RouterProvider
├── main.tsx       # entry; initTheme()
└── index.css      # Tailwind + theme tokens (--ink-*, --accent-*)
```

## Routing (`routes/router.tsx`)

| Path | Page | Protected |
| --- | --- | --- |
| `/login` | `LoginPage` | public |
| `/` | `RepositoryListPage` | `RequireAuth` |
| `/discover` | `DiscoverPage` | public |
| `/discover/r` | `RepositoryAnalysesPage` | public |
| `/u/:username` | `ProfilePage` | public |
| `/stars` | `StarredPage` | `RequireAuth` |
| `/repos/:repositoryId/overview` | `RepositoryDashboardPage` | public |
| `/repos/:repositoryId/graph` | `DependencyGraphPage` | public |
| `/repos/:repositoryId/complexity` | `ComplexityPage` | public |
| `/repos/:repositoryId/dead-code` | `DeadCodePage` | public |
| `/repos/:repositoryId/architecture` | `ArchitecturePage` | public |
| `/repos/:repositoryId/impact` | `ImpactAnalysisPage` | public |
| `/repos/:repositoryId/chat` | `AIAssistantPage` | public |
| `*` | `NotFoundPage` | public |

All routes except `/login` render inside `AppShell` (sidebar + topbar + scrolling main).
`RequireAuth` shows a spinner while `useMe()` resolves, then redirects to `/login` if
unauthenticated.

## Layout system

- **`AppShell`** — three zones: a sidebar (desktop in-flow, collapsible to an icon rail;
  mobile an off-canvas drawer that closes on navigation/Escape), a sticky `Topbar`, and a
  scrolling `<main>`.
- **`Sidebar`** — workspace nav (Repositories/Discover/Stars) + repo-scoped nav (Overview,
  Dependencies, Complexity, Dead code, Architecture, Impact, AI assistant) when a repo is
  in the URL.
- **`Topbar`** — hamburger (mobile) / sidebar toggle (desktop), theme toggle, user menu.

## Responsive strategy

- Tailwind breakpoints (`sm` 640, `md` 768, `lg` 1024, `xl` 1280); `lg` is the
  mobile/desktop nav boundary.
- Pages use `p-4 sm:p-6`; grids collapse `grid-cols-1 → sm:2 → lg:3 → xl:4`.
- `<main>` uses `scrollbar-gutter: stable` so a classic scrollbar never paints over card
  content (this fixed a real "card cut off on the right" bug).
- The complexity chart switches to **horizontal bars** under `639px` (readable file labels)
  via `useMediaQuery`.
- The dependency graph and chat have dedicated mobile treatments (drawer rails, pinned
  composer); see their feature docs.

## Build & tooling

- Scripts: `dev` (Vite), `build` (`tsc -b && vite build`), `lint` (ESLint, **0 warnings**),
  `typecheck`, `test` (Vitest), `test:e2e` (Playwright).
- `tsconfig`: `strict`, `noUnusedLocals/Parameters`, `noUncheckedIndexedAccess`,
  `noImplicitReturns` — strict TS catches a lot at build time.
- `vite.config.ts`: `@` → `src` alias; dev proxy `/api` → backend; manual vendor chunks
  (`vendor-react`, `vendor-graph`, `vendor-charts`, `vendor-mermaid`, `vendor-query`).
- `tailwind.config.js`: `darkMode: "class"`; colors are CSS-variable tokens (`ink`,
  `accent`, `surface`, `success/warning/danger`) for alpha support.

## Theming
- `themeStore` persists `light`/`dark` to `localStorage`, applies `.dark` to `<html>`.
- `initTheme()` runs in `main.tsx` before render to avoid a flash.
- Tokens in `index.css`: neutral `--ink-*` (inverts in dark), brand `--accent-*` (Discord
  blurple). Dark mode flips foreground accent ramps while keeping `accent-500/600`
  saturated for buttons/bubbles.
