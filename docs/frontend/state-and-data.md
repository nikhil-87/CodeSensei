# Frontend State & Data Fetching

Three concerns are kept separate: **server state** (TanStack Query), **client/UI state**
(Zustand), and **transport** (axios + a custom SSE client).

## Server state — TanStack Query

Configured in `lib/queryClient.ts`: `staleTime` 60s, `gcTime` 5m,
`refetchOnWindowFocus: false`, retry only 5xx once (never 4xx). Hooks live in `hooks/`.

| Hook | Query key | Endpoint | Notes |
| --- | --- | --- | --- |
| `useRepositories(params)` | `["repositories","list",params]` | `RepositoriesApi.list` | keepPreviousData |
| `useRepository(id)` | `["repositories","detail",id]` | `RepositoriesApi.get` | enabled if id |
| `useCreateRepository()` / `useDeleteRepository()` / `useSetVisibility()` | mutations | repo CRUD | invalidate repo queries |
| `useAnalysisJobs` / `useLatestAnalysisJob` | `["analysis",id,…]` | jobs | |
| `useTriggerAnalysis()` | mutation | analyze | invalidate analysis + repo |
| `useAnalysisProgress(id, enabled)` | SSE | `/events` | async iterator; stops on terminal |
| `useDependencyGraph` / `useComplexity` / `useDeadCode` / `useArchitecture` | insight keys | reads | 5-min staleness |
| `useChatSessions` / `useSessionMessages` | chat keys | sessions/messages | |
| `useCreateChatSession` / `useRenameChatSession` / `useDeleteChatSession` | mutations | sessions | optimistic insert at head |
| `useSessionChat(id, opts)` | SSE | `/chat-sessions/{id}/chat` | streams `ChatTokenEvent` |
| `useMe()` | `["auth","me"]` | `/auth/me` | `User\|null`, never retries |
| `useLogout()` / `useDevLogin()` | mutations | auth | clear/seed cache |
| `useDiscover` / `useStarredRepositories` / `useProfile` / `useProfileRepositories` | list keys | discovery/social | keepPreviousData |
| `useDiscoverRepository(url, branch)` | `["discover","repository",url,branch]` | `/discover/repository` | repository overview + public analyses |

Custom non-query hooks: `useDebouncedValue(value, ms)` (search), `useMediaQuery(query)`
(responsive), star/dependency toggle helpers.

## Client state — Zustand stores (`store/`)

### `uiStore`
`sidebarCollapsed` (+ `toggleSidebar`/`setSidebar`) for the desktop rail; `mobileNavOpen`
(+ `openMobileNav`/`closeMobileNav`) for the off-canvas drawer.

### `themeStore`
`theme: "light"|"dark"` with `setTheme`/`toggleTheme` (persists to localStorage, toggles
`.dark` on `<html>`); `initTheme()` runs before first paint.

### `nodeContextStore`
The glue for "Ask AI about this node". Holds `repositoryId`, `attached: AttachedFile[]`,
and a one-shot `pendingPrompt`. The graph/architecture inspector calls
`attachFile(repoId, file)` + `setPendingPrompt(prompt)`; the chat panel calls
`consumePendingPrompt()` on mount to auto-send. Scoped per repo so context never leaks
across repositories.

## Transport

### `lib/api.ts`
Axios instance rooted at `/api/v1`, `withCredentials: true` (sends the session cookie). It
does **not** throw on 4xx — it returns a typed `ApiError(message, status, code, details)`
with human-friendly messages. Retries 5xx once.

### `lib/sse.ts`
A custom async-generator SSE client (`openSse`) that — unlike the native `EventSource` —
supports **POST** (needed for chat, which sends a body). Parses `event:`/`data:` framing,
throws on non-2xx, and ends iteration on close or `AbortSignal`.

## Data lifecycle example — sending a chat message

```mermaid
sequenceDiagram
  participant UI as ChatPanel
  participant H as useSessionChat
  participant SSE as lib/sse.openSse (POST)
  participant BE as Backend
  UI->>H: send(question, attachedPaths)
  H->>SSE: POST /chat-sessions/{id}/chat
  SSE-->>H: event token … (append to draft)
  SSE-->>H: event citations … (attach to message)
  SSE-->>H: event done
  H->>UI: finalize message; invalidate session list (title/order)
```
