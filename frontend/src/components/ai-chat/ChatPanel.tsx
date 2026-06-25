import {
  Check,
  ChevronRight,
  FileCode2,
  Loader2,
  MessageSquarePlus,
  PanelLeft,
  Pencil,
  Send,
  Square,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";

import {
  chatSessionQueryKeys,
  useChatSessions,
  useCreateChatSession,
  useDeleteChatSession,
  useRenameChatSession,
} from "@/hooks/useChatSessions";
import { useSessionChat } from "@/hooks/useSessionChat";
import { cn } from "@/lib/format";
import { useNodeContextStore } from "@/store/nodeContextStore";
import type { AttachedContext, ChatCitation, ChatSession } from "@/types/api";

interface ChatPanelProps {
  repositoryId: string;
}

export function ChatPanel({ repositoryId }: ChatPanelProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const urlSession = searchParams.get("session");

  const { data: sessionsPage, isLoading: sessionsLoading } =
    useChatSessions(repositoryId);
  const createSession = useCreateChatSession(repositoryId);
  const renameSession = useRenameChatSession(repositoryId);
  const deleteSession = useDeleteChatSession(repositoryId);

  const sessions = useMemo(() => sessionsPage?.items ?? [], [sessionsPage]);
  const [activeId, setActiveId] = useState<string | null>(urlSession);
  // Mobile-only: the session rail slides over as a drawer.
  const [railOpen, setRailOpen] = useState(false);

  // Keep the active session valid: honour the URL, else fall back to the most
  // recent session, else nothing (empty state prompts the user to start one).
  useEffect(() => {
    if (sessionsLoading) return;
    const ids = new Set(sessions.map((s) => s.id));
    if (activeId && ids.has(activeId)) return;
    if (urlSession && ids.has(urlSession)) {
      setActiveId(urlSession);
      return;
    }
    setActiveId(sessions[0]?.id ?? null);
  }, [sessions, sessionsLoading, activeId, urlSession]);

  // Reflect the active session in the URL so it's deep-linkable / restorable.
  const selectSession = useCallback(
    (id: string | null) => {
      setActiveId(id);
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          if (id) next.set("session", id);
          else next.delete("session");
          return next;
        },
        { replace: true },
      );
    },
    [setSearchParams],
  );

  const handleNewChat = useCallback(async () => {
    const created = await createSession.mutateAsync(undefined);
    selectSession(created.id);
  }, [createSession, selectSession]);

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteSession.mutateAsync(id);
      if (activeId === id) selectSession(null);
    },
    [deleteSession, activeId, selectSession],
  );

  const handleRename = useCallback(
    async (id: string, title: string) => {
      await renameSession.mutateAsync({ sessionId: id, title });
    },
    [renameSession],
  );

  return (
    <div className="relative flex min-h-0 flex-1 overflow-hidden">
      {/* Desktop: in-flow side rail. */}
      <div className="hidden lg:flex">
        <SessionRail
          sessions={sessions}
          loading={sessionsLoading}
          activeId={activeId}
          creating={createSession.isPending}
          onSelect={selectSession}
          onNew={handleNewChat}
          onRename={handleRename}
          onDelete={handleDelete}
        />
      </div>

      {/* Mobile: overlay drawer toggled from the conversation header. */}
      {railOpen && (
        <div className="absolute inset-0 z-20 lg:hidden">
          <div
            className="absolute inset-0 bg-ink-900/40"
            onClick={() => setRailOpen(false)}
          />
          <div className="absolute inset-y-0 left-0 w-[80%] max-w-xs bg-surface p-3 shadow-elev">
            <SessionRail
              sessions={sessions}
              loading={sessionsLoading}
              activeId={activeId}
              creating={createSession.isPending}
              onSelect={(id) => {
                selectSession(id);
                setRailOpen(false);
              }}
              onNew={() => {
                void handleNewChat();
                setRailOpen(false);
              }}
              onRename={handleRename}
              onDelete={handleDelete}
              mobile
            />
          </div>
        </div>
      )}

      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        {activeId ? (
          <Conversation
            key={activeId}
            repositoryId={repositoryId}
            sessionId={activeId}
            onOpenRail={() => setRailOpen(true)}
          />
        ) : (
          <EmptyConversation
            onNew={handleNewChat}
            creating={createSession.isPending}
            hasSessions={sessions.length > 0}
            onOpenRail={() => setRailOpen(true)}
          />
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Session rail
// ---------------------------------------------------------------------------
function SessionRail({
  sessions,
  loading,
  activeId,
  creating,
  onSelect,
  onNew,
  onRename,
  onDelete,
  mobile = false,
}: {
  sessions: ChatSession[];
  loading: boolean;
  activeId: string | null;
  creating: boolean;
  onSelect: (id: string) => void;
  onNew: () => void;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  mobile?: boolean;
}) {
  return (
    <aside
      className={cn(
        "flex shrink-0 flex-col border-r border-ink-100 pr-3",
        mobile ? "h-full w-full border-r-0 pr-0" : "w-60",
      )}
    >
      <button
        type="button"
        onClick={onNew}
        disabled={creating}
        className="focus-ring mb-3 inline-flex items-center justify-center gap-2 rounded-lg border border-accent-200 bg-accent-50 px-3 py-2 text-sm font-medium text-accent-800 transition-colors hover:bg-accent-100 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {creating ? (
          <Loader2 className="h-4 w-4 animate-spin" />
        ) : (
          <MessageSquarePlus className="h-4 w-4" />
        )}
        New chat
      </button>

      <div className="flex-1 space-y-0.5 overflow-y-auto">
        {loading && (
          <p className="px-2 py-2 text-xs text-ink-400">Loading conversations…</p>
        )}
        {!loading && sessions.length === 0 && (
          <p className="px-2 py-2 text-xs text-ink-400">
            No conversations yet. Start one above.
          </p>
        )}
        {sessions.map((s) => (
          <SessionRow
            key={s.id}
            session={s}
            active={s.id === activeId}
            onSelect={() => onSelect(s.id)}
            onRename={onRename}
            onDelete={onDelete}
          />
        ))}
      </div>
    </aside>
  );
}

function SessionRow({
  session,
  active,
  onSelect,
  onRename,
  onDelete,
}: {
  session: ChatSession;
  active: boolean;
  onSelect: () => void;
  onRename: (id: string, title: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(session.title);
  const [confirming, setConfirming] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.focus();
  }, [editing]);

  const commitRename = async () => {
    const title = value.trim();
    setEditing(false);
    if (title && title !== session.title) {
      await onRename(session.id, title);
    } else {
      setValue(session.title);
    }
  };

  if (editing) {
    return (
      <div className="flex items-center gap-1 rounded-md bg-ink-50 px-1.5 py-1">
        <input
          ref={inputRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") void commitRename();
            if (e.key === "Escape") {
              setValue(session.title);
              setEditing(false);
            }
          }}
          maxLength={200}
          className="min-w-0 flex-1 rounded border border-ink-200 bg-surface px-1.5 py-0.5 text-xs text-ink-900 focus:border-accent-400 focus:outline-none"
        />
        <button
          type="button"
          onClick={() => void commitRename()}
          aria-label="Save name"
          className="focus-ring rounded p-1 text-accent-600 hover:bg-accent-100"
        >
          <Check className="h-3.5 w-3.5" />
        </button>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "group flex items-center gap-1 rounded-md px-2 py-1.5 text-sm transition-colors",
        active ? "bg-accent-50 text-accent-900" : "text-ink-700 hover:bg-ink-50",
      )}
    >
      <button
        type="button"
        onClick={onSelect}
        className="focus-ring min-w-0 flex-1 truncate text-left"
        title={session.title}
      >
        {session.title}
      </button>
      {confirming ? (
        <span className="flex items-center gap-0.5">
          <button
            type="button"
            onClick={() => void onDelete(session.id)}
            aria-label="Confirm delete"
            className="focus-ring rounded p-1 text-danger-500 hover:bg-danger-100"
          >
            <Check className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            aria-label="Cancel delete"
            className="focus-ring rounded p-1 text-ink-400 hover:bg-ink-100"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </span>
      ) : (
        <span className="flex items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
          <button
            type="button"
            onClick={() => {
              setValue(session.title);
              setEditing(true);
            }}
            aria-label="Rename conversation"
            className="focus-ring rounded p-1 text-ink-400 hover:bg-ink-100 hover:text-ink-700"
          >
            <Pencil className="h-3.5 w-3.5" />
          </button>
          <button
            type="button"
            onClick={() => setConfirming(true)}
            aria-label="Delete conversation"
            className="focus-ring rounded p-1 text-ink-400 hover:bg-danger-100 hover:text-danger-500"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </button>
        </span>
      )}
    </div>
  );
}

function EmptyConversation({
  onNew,
  creating,
  hasSessions,
  onOpenRail,
}: {
  onNew: () => void;
  creating: boolean;
  hasSessions: boolean;
  onOpenRail?: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col">
      {onOpenRail && (
        <div className="mb-2 lg:hidden">
          <button
            type="button"
            onClick={onOpenRail}
            className="focus-ring inline-flex items-center gap-1.5 rounded-md border border-ink-200 px-2.5 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50"
          >
            <PanelLeft className="h-3.5 w-3.5" /> Conversations
          </button>
        </div>
      )}
      <div className="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
        <div className="rounded-full bg-accent-50 p-3 text-accent-600">
          <MessageSquarePlus className="h-6 w-6" />
        </div>
        <p className="text-sm text-ink-500">
          {hasSessions
            ? "Select a conversation or start a new one."
            : "Start a conversation to ask about this repository."}
        </p>
        <button
          type="button"
          onClick={onNew}
          disabled={creating}
          className="focus-ring inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-700 disabled:opacity-60"
        >
          {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
          New chat
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Conversation (bound to one session)
// ---------------------------------------------------------------------------
function Conversation({
  repositoryId,
  sessionId,
  onOpenRail,
}: {
  repositoryId: string;
  sessionId: string;
  onOpenRail?: () => void;
}) {
  const queryClient = useQueryClient();
  const { turns, draft, status, error, send, cancel } = useSessionChat(sessionId, {
    onAssistantDone: () => {
      // Refresh the rail so the auto-generated title / ordering updates.
      void queryClient.invalidateQueries({
        queryKey: chatSessionQueryKeys.list(repositoryId),
      });
    },
  });

  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const autoSentRef = useRef(false);

  const attached = useNodeContextStore((s) => s.attached);
  const removeFile = useNodeContextStore((s) => s.removeFile);
  const consumePendingPrompt = useNodeContextStore((s) => s.consumePendingPrompt);

  const isStreaming = status === "streaming";
  const isLoading = status === "loading";
  const canSend = input.trim().length > 0 && !isStreaming && !isLoading;

  const attachedContext = useMemo<AttachedContext[]>(
    () => attached.map((f) => ({ path: f.path, language: f.language })),
    [attached],
  );

  // Auto-send a question queued from the graph/inspector "Ask AI" actions.
  useEffect(() => {
    if (autoSentRef.current || isLoading) return;
    const queued = consumePendingPrompt();
    if (queued) {
      autoSentRef.current = true;
      void send(queued, attachedContext);
    }
  }, [consumePendingPrompt, send, attachedContext, isLoading]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [turns, draft]);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canSend) return;
    const q = input.trim();
    setInput("");
    await send(q, attachedContext);
  };

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col pl-0 lg:pl-4">
      {onOpenRail && (
        <div className="mb-1 lg:hidden">
          <button
            type="button"
            onClick={onOpenRail}
            className="focus-ring inline-flex items-center gap-1.5 rounded-md border border-ink-200 px-2.5 py-1.5 text-xs font-medium text-ink-600 hover:bg-ink-50"
          >
            <PanelLeft className="h-3.5 w-3.5" /> Conversations
          </button>
        </div>
      )}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto px-1 py-2">
        {isLoading && (
          <div className="flex items-center justify-center gap-2 py-8 text-sm text-ink-400">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading conversation…
          </div>
        )}

        {!isLoading && turns.length === 0 && !isStreaming && (
          <div className="rounded-lg border border-dashed border-ink-200 bg-surface p-6 text-center text-sm text-ink-500">
            Ask a question about this repository — CodeSensei will cite the files it
            used.
          </div>
        )}

        {turns.map((t) => (
          <Bubble key={t.id} role={t.role}>
            {t.attached && t.attached.length > 0 && (
              <AttachedBadges attached={t.attached} />
            )}
            {t.role === "assistant" ? (
              <AssistantText content={t.content} citations={t.citations ?? []} />
            ) : (
              <p className="whitespace-pre-wrap">{t.content}</p>
            )}
            {t.citations && t.citations.length > 0 && (
              <Citations citations={t.citations} />
            )}
          </Bubble>
        ))}

        {isStreaming && draft && (
          <Bubble role="assistant" pending>
            <p className="whitespace-pre-wrap">{stripCitations(draft)}</p>
          </Bubble>
        )}
        {isStreaming && !draft && (
          <Bubble role="assistant" pending>
            <span className="inline-flex gap-1">
              <Dot /> <Dot delay={0.15} /> <Dot delay={0.3} />
            </span>
          </Bubble>
        )}

        {error && (
          <div className="rounded-lg bg-danger-100 px-3 py-2 text-sm text-danger-500">
            {error}
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="mt-3 border-t border-ink-100 pt-3">
        {attached.length > 0 && (
          <div className="mb-2 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-medium text-ink-400">Context:</span>
            {attached.map((f) => (
              <span
                key={f.id}
                className="inline-flex max-w-[16rem] items-center gap-1 rounded-md border border-accent-200 bg-accent-50 py-0.5 pl-1.5 pr-1 text-[11px] font-medium text-accent-800"
                title={f.path}
              >
                <FileCode2 className="h-3 w-3 shrink-0" />
                <span className="truncate">{f.path.split("/").pop()}</span>
                <button
                  type="button"
                  onClick={() => removeFile(f.id)}
                  aria-label={`Remove ${f.path} from context`}
                  className="focus-ring rounded p-0.5 text-accent-600 hover:bg-accent-100 hover:text-accent-900"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
          </div>
        )}
        <div className="flex items-end gap-2 rounded-xl border border-ink-200 bg-surface p-2 shadow-sm transition-colors focus-within:border-accent-400 focus-within:ring-2 focus-within:ring-accent-500/30">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about this repository…"
            rows={1}
            aria-label="Message CodeSensei"
            disabled={isLoading}
            className="max-h-40 min-h-[40px] flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm text-ink-900 placeholder:text-ink-400 focus:outline-none focus:ring-0 disabled:opacity-60"
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSubmit(e as unknown as React.FormEvent);
              }
            }}
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={cancel}
              aria-label="Stop generating"
              title="Stop generating"
              className="focus-ring inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-ink-200 bg-surface text-ink-700 transition-colors hover:bg-ink-100 active:bg-ink-200"
            >
              <Square className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="submit"
              disabled={!canSend}
              aria-label="Send message"
              title="Send message"
              className="focus-ring inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-accent-600 text-white transition-colors hover:bg-accent-700 active:bg-accent-800 disabled:cursor-not-allowed disabled:bg-accent-300"
            >
              <Send className="h-4 w-4" />
            </button>
          )}
        </div>

        <div className="mt-2 flex items-center justify-between px-1">
          <p className="text-xs text-ink-400">
            <Kbd>Enter</Kbd> to send · <Kbd>Shift</Kbd>+<Kbd>Enter</Kbd> for a new line
          </p>
        </div>
      </form>
    </div>
  );
}

function AttachedBadges({ attached }: { attached: AttachedContext[] }) {
  return (
    <div className="mb-1.5 flex flex-wrap gap-1">
      {attached.map((a, i) => (
        <span
          key={`${a.path}-${i}`}
          className="inline-flex items-center gap-1 rounded bg-white/15 px-1.5 py-0.5 text-[10px] font-medium"
          title={a.path}
        >
          <FileCode2 className="h-2.5 w-2.5" />
          {a.path.split("/").pop()}
        </span>
      ))}
    </div>
  );
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded border border-ink-200 bg-ink-50 px-1 py-0.5 font-sans text-[10px] font-medium text-ink-500">
      {children}
    </kbd>
  );
}

function Bubble({
  role,
  children,
  pending,
}: {
  role: "user" | "assistant";
  children: React.ReactNode;
  pending?: boolean;
}) {
  return (
    <div className={cn("flex", role === "user" ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-4 py-2.5 text-sm leading-relaxed shadow-card",
          role === "user"
            ? "bg-accent-600 text-white"
            : "bg-surface text-ink-900",
          pending && "animate-pulse",
        )}
      >
        {children}
      </div>
    </div>
  );
}

function Citations({ citations }: { citations: ChatCitation[] }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="mt-3 border-t border-ink-100 pt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center gap-1.5 text-xs font-medium text-ink-500 transition-colors hover:text-ink-700 focus-ring rounded"
      >
        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 shrink-0 transition-transform",
            open && "rotate-90",
          )}
        />
        <span>
          {citations.length} {citations.length === 1 ? "source" : "sources"}
        </span>
      </button>

      {open && (
        <ol className="mt-2 space-y-1.5 pl-1">
          {citations.map((c, i) => (
            <li
              key={`${c.file_path}-${c.line_start}-${i}`}
              className="flex items-start gap-2 text-xs"
            >
              <span className="mt-px inline-flex h-4 min-w-4 shrink-0 items-center justify-center rounded bg-accent-100 px-1 text-[10px] font-semibold leading-none text-accent-700">
                {i + 1}
              </span>
              <span className="min-w-0">
                <span className="break-all font-mono text-accent-700">
                  {c.file_path}
                </span>
                <span className="ml-1 text-ink-500">
                  L{c.line_start}–{c.line_end}
                  {c.symbol ? ` · ${c.symbol}` : ""}
                </span>
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

// Inline citation markers the model emits, e.g. `[path/to/file.ts:120-140]`,
// sometimes wrapped in backticks. We strip these from the prose and replace
// them with a small numbered marker that maps to the sources dropdown.
const INLINE_CITATION_RE =
  /`?\[`?\s*([^\]`]+?)\s*:\s*(\d+)(?:\s*-\s*(\d+))?\s*`?\]`?/g;

function buildCitationNumbers(citations: ChatCitation[]) {
  const exact = new Map<string, number>();
  const byPath = new Map<string, number>();
  citations.forEach((c, i) => {
    exact.set(`${c.file_path}:${c.line_start}-${c.line_end}`, i + 1);
    if (!byPath.has(c.file_path)) byPath.set(c.file_path, i + 1);
  });
  return { exact, byPath };
}

/** Remove inline citation tokens from text (used for the streaming preview). */
function stripCitations(text: string): string {
  return text.replace(INLINE_CITATION_RE, "").replace(/[ \t]{2,}/g, " ");
}

function CitationMarker({ n, label }: { n: number; label: string }) {
  return (
    <sup
      title={label}
      className="mx-0.5 inline-flex h-3.5 min-w-3.5 items-center justify-center rounded bg-accent-100 px-1 align-super text-[9px] font-semibold leading-none text-accent-700"
    >
      {n}
    </sup>
  );
}

/**
 * Render an assistant answer: prose with inline `[path:lines]` citation tokens
 * replaced by small numbered markers that correspond to the sources dropdown.
 * Unknown citations (not in the sources list) are simply dropped so the user
 * never sees raw file-path noise.
 */
function AssistantText({
  content,
  citations,
}: {
  content: string;
  citations: ChatCitation[];
}) {
  if (citations.length === 0) {
    return <p className="whitespace-pre-wrap">{stripCitations(content).trim()}</p>;
  }

  const { exact, byPath } = buildCitationNumbers(citations);
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let key = 0;
  INLINE_CITATION_RE.lastIndex = 0;
  let m: RegExpExecArray | null;
  while ((m = INLINE_CITATION_RE.exec(content)) !== null) {
    const [full, path, start, end] = m;
    if (m.index > last) nodes.push(content.slice(last, m.index));
    const n = path
      ? (end ? exact.get(`${path}:${start}-${end}`) : undefined) ??
        byPath.get(path)
      : undefined;
    if (n) {
      const label = end ? `${path}:${start}-${end}` : `${path}:${start}`;
      nodes.push(<CitationMarker key={`cm-${key++}`} n={n} label={label} />);
    }
    last = m.index + full.length;
  }
  if (last < content.length) nodes.push(content.slice(last));

  return <p className="whitespace-pre-wrap">{nodes}</p>;
}

function Dot({ delay = 0 }: { delay?: number }) {
  return (
    <span
      className="inline-block h-1.5 w-1.5 animate-bounce rounded-full bg-ink-400"
      style={{ animationDelay: `${delay}s` }}
    />
  );
}
