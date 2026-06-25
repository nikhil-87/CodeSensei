# Feature: AI Chat & Sessions

## What it does
A conversational assistant that answers natural-language questions about a repository,
grounded in its actual source via RAG, streaming tokens in real time and returning numbered
citations. Conversations are persistent, user-private **sessions** per repo, and users can
**tag specific files** as guaranteed context.

## Why it exists
This is the headline feature: instead of reading code, *ask* it. Grounding + citations make
answers trustworthy; sessions make it a usable, returnable workflow.

## User workflow
1. Open `…/chat` (gated until analysis is ready).
2. Pick or create a session in the rail (desktop side rail / mobile drawer).
3. Type a question (optionally with files tagged from the graph/architecture inspector).
4. Watch the answer stream in; expand citations to jump to source; continue the thread.

## Backend implementation
- **Stateless:** `POST /ai/chat` → `AIService.stream_chat` (client supplies history; no DB
  writes).
- **Session:** `POST /chat-sessions/{id}/chat` → `ChatSessionService.stream_chat`:
  loads prior turns, saves the user turn, retrieves + streams, saves the assistant turn
  (content + citations + attached context), bumps `last_activity_at`. Ownership enforced.
- **RAG core:** embed question → ChromaDB top-k (+ tagged files guaranteed) → prompt →
  LLM stream → SSE `token`/`citations`/`done`/`error`. See
  [../ai/rag-pipeline.md](../ai/rag-pipeline.md).
- **Session CRUD:** create/list/get/rename/delete in `chat_sessions.py`.

## Frontend implementation
- **`ChatPanel`:** session rail, transcript with numbered citations, composer pinned above
  the mobile keyboard, attach-context chips, streaming + abort. The `Card` wrapper exposes
  `contentClassName` so the flex-height scroll chain works (composer stays pinned, messages
  scroll internally).
- **`useSessionChat`:** drives the POST SSE stream via `lib/sse.ts`.
- **`SessionPickerModal`:** the "Ask AI about this file" entry point — new/existing session,
  tags the file, preserves the starter prompt.

## Tables involved
- `chat_sessions` (per user+repo, `last_activity_at`, title), `chat_messages` (role,
  content, `citations` JSONB, `attached_context` JSONB).

## APIs
Session CRUD + `…/messages` + `…/chat` (SSE) under `/chat-sessions`; plus stateless
`/ai/chat`.

## Edge cases handled
- **Tagged file not in top-k** — forced into context (guaranteed slot).
- **Indexing degraded** — chat still answers from whatever is indexed; quality may drop.
- **Abort mid-stream** — `AbortSignal` ends the SSE iterator; partial draft preserved.
- **Auto-title** — first message seeds the session title; the rail re-orders by activity.
- **Mobile keyboard** — composer stays visible; message list scrolls internally.

## Security considerations
- Sessions are strictly per user; every session route re-checks ownership.
- Citations only reference files the repo actually contains.
- Prompt-injection from repo content is a known LLM risk; the system prompt constrains the
  model and the surface is read-only. See [../security/threat-model.md](../security/threat-model.md).

## Future improvements
- Retrieval re-ranking; larger context via summarization.
- Multi-repo / cross-repo chat.
- Streaming citations earlier (as chunks are selected).
