/**
 * Session-based streaming chat hook.
 *
 * Unlike the old stateless ``useChatStream``, this hook is bound to a
 * persisted :type:`ChatSession`:
 *
 * - History is loaded from the server (session memory survives reloads).
 * - The user + assistant turns are persisted server-side; we don't resend
 *   the full transcript — the backend rebuilds context from storage.
 * - Attached files are sent as structured context, not string-prefixed.
 *
 * State machine: idle ─send()▶ streaming ─token*▶ streaming ─done▶ idle
 *                                                  └─error▶ error
 */
import { useCallback, useEffect, useRef, useState } from "react";

import { ChatSessionsApi } from "@/api/chatSessions";
import { useSessionMessages } from "@/hooks/useChatSessions";
import type { AttachedContext, ChatCitation } from "@/types/api";

export interface ChatTurn {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: ChatCitation[];
  attached?: AttachedContext[];
}

export interface UseSessionChatResult {
  turns: ChatTurn[];
  draft: string;
  status: "idle" | "loading" | "streaming" | "error";
  error: string | null;
  send: (question: string, attached?: AttachedContext[]) => Promise<void>;
  cancel: () => void;
}

interface Options {
  /** Fired after the assistant turn completes (used to refresh the rail). */
  onAssistantDone?: () => void;
}

export function useSessionChat(
  sessionId: string | undefined,
  options: Options = {},
): UseSessionChatResult {
  const { onAssistantDone } = options;
  const { data: history, isLoading } = useSessionMessages(sessionId);

  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState<UseSessionChatResult["status"]>("idle");
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const seededFor = useRef<string | null>(null);

  // Seed the transcript from persisted history whenever the session changes.
  useEffect(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (!sessionId) {
      setTurns([]);
      seededFor.current = null;
      setStatus("idle");
      setDraft("");
      setError(null);
      return;
    }
    if (history && seededFor.current !== sessionId) {
      setTurns(
        history.items.map((m) => ({
          id: m.id,
          role: m.role,
          content: m.content,
          citations: m.citations ?? undefined,
          attached: m.attached_context ?? undefined,
        })),
      );
      seededFor.current = sessionId;
      setStatus("idle");
      setDraft("");
      setError(null);
    }
  }, [sessionId, history]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setStatus("idle");
    setDraft("");
  }, []);

  const send = useCallback(
    async (question: string, attached: AttachedContext[] = []) => {
      const sid = sessionId;
      if (!sid || !question.trim()) return;
      abortRef.current?.abort();
      const controller = new AbortController();
      abortRef.current = controller;

      const userTurn: ChatTurn = {
        id: randomId(),
        role: "user",
        content: question.trim(),
        attached: attached.length ? attached : undefined,
      };
      setTurns((prev) => [...prev, userTurn]);
      setDraft("");
      setStatus("streaming");
      setError(null);

      let buffer = "";
      let citations: ChatCitation[] | undefined;

      try {
        for await (const evt of ChatSessionsApi.streamChat(
          sid,
          { question: question.trim(), attached, top_k: 8 },
          controller.signal,
        )) {
          switch (evt.event) {
            case "citations":
              citations = evt.citations;
              break;
            case "token":
              buffer += evt.content;
              setDraft(buffer);
              break;
            case "done": {
              setTurns((prev) => [
                ...prev,
                { id: randomId(), role: "assistant", content: buffer, citations },
              ]);
              setDraft("");
              setStatus("idle");
              onAssistantDone?.();
              break;
            }
            case "error":
              setError(evt.error);
              setStatus("error");
              break;
          }
        }
      } catch (e) {
        if ((e as Error).name === "AbortError") return;
        setError((e as Error).message || "Chat failed");
        setStatus("error");
      }
    },
    [sessionId, onAssistantDone],
  );

  const effectiveStatus: UseSessionChatResult["status"] =
    status === "idle" && isLoading && sessionId ? "loading" : status;

  return { turns, draft, status: effectiveStatus, error, send, cancel };
}

function randomId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2);
}
