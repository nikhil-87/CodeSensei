# Frontend — React + TypeScript + Vite SPA

Single-page application that consumes the FastAPI backend. Renders dependency
graphs (React Flow), metric charts (Recharts), source code (Monaco), and an
AI chat panel.

## Layout

```
frontend/
├── src/
│   ├── api/              # Generated + handwritten API clients (axios + TanStack Query)
│   ├── components/       # Presentational components, grouped by domain
│   │   ├── common/       # Buttons, modals, layout primitives
│   │   ├── repository/   # Repo cards, repo selector, branch picker
│   │   ├── graph/        # React Flow node/edge components
│   │   ├── metrics/      # Recharts wrappers
│   │   ├── ai-chat/      # Chat bubbles, message list, prompt input
│   │   └── layout/       # AppShell, Sidebar, Topbar
│   ├── features/         # Feature slices (state + container components)
│   │   ├── repositories/
│   │   ├── dependency-graph/
│   │   ├── dead-code/
│   │   ├── complexity/
│   │   ├── impact-analysis/
│   │   ├── architecture/
│   │   └── ai-assistant/
│   ├── hooks/            # Shared React hooks (useDebounce, useSse, useToast)
│   ├── lib/              # Cross-cutting libs (queryClient, axios instance, sse client)
│   ├── pages/            # Route-level components
│   ├── routes/           # React Router config
│   ├── store/            # Zustand stores for non-server state
│   ├── types/            # Shared TS types mirroring backend DTOs
│   ├── utils/            # Pure helpers (formatters, validators)
│   ├── App.tsx
│   └── main.tsx
├── public/               # Static assets served as-is
├── tests/
│   ├── unit/             # React Testing Library
│   ├── e2e/              # Playwright specs
│   └── setup.ts
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── tailwind.config.js
├── postcss.config.js
├── .eslintrc.cjs
├── playwright.config.ts
└── Dockerfile            # Multi-stage: node build → nginx static serve
```

## Conventions

- **One feature folder per top-level route.** Each owns its containers, slices, and tests.
- **No `any`.** TypeScript strict mode is enforced via `tsconfig`.
- **Server state lives in TanStack Query**, never in Zustand or Redux.
- **Tailwind only.** No CSS-in-JS, no styled-components.
- **Monaco loaded lazily** to keep the initial bundle under 300 KB gzip.

## Build & run

```bash
npm ci
npm run dev          # http://localhost:5173
npm run build        # static bundle in dist/
npm test             # Vitest + RTL
npm run test:e2e     # Playwright (assumes backend at :8000)
```
