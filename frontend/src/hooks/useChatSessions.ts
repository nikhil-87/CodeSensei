import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ChatSessionsApi } from "@/api/chatSessions";
import type {
  ChatSession,
  ChatSessionUpdateInput,
  Paginated,
} from "@/types/api";

export const chatSessionQueryKeys = {
  all: ["chat-sessions"] as const,
  list: (repositoryId: string) =>
    [...chatSessionQueryKeys.all, "list", repositoryId] as const,
  messages: (sessionId: string) =>
    [...chatSessionQueryKeys.all, "messages", sessionId] as const,
};

export function useChatSessions(repositoryId: string | undefined) {
  return useQuery({
    queryKey: chatSessionQueryKeys.list(repositoryId ?? ""),
    queryFn: () => ChatSessionsApi.list(repositoryId as string, { page_size: 100 }),
    enabled: Boolean(repositoryId),
  });
}

export function useSessionMessages(sessionId: string | undefined) {
  return useQuery({
    queryKey: chatSessionQueryKeys.messages(sessionId ?? ""),
    queryFn: () => ChatSessionsApi.messages(sessionId as string, { page_size: 200 }),
    enabled: Boolean(sessionId),
  });
}

export function useCreateChatSession(repositoryId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (title?: string) =>
      ChatSessionsApi.create(repositoryId as string, title ? { title } : {}),
    onSuccess: (created) => {
      if (!repositoryId) return;
      const key = chatSessionQueryKeys.list(repositoryId);
      // Optimistically insert the new session at the top of the cached list so
      // the panel can switch to it immediately. Without this, the list-driven
      // "pick a valid active session" effect would briefly snap back to the
      // previous conversation while the refetch is in flight.
      qc.setQueryData<Paginated<ChatSession>>(key, (old) => {
        if (!old) return old;
        if (old.items.some((s) => s.id === created.id)) return old;
        return { ...old, items: [created, ...old.items], total: old.total + 1 };
      });
      qc.invalidateQueries({ queryKey: key });
    },
  });
}

export function useRenameChatSession(repositoryId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ sessionId, title }: { sessionId: string } & ChatSessionUpdateInput) =>
      ChatSessionsApi.rename(sessionId, { title }),
    onSuccess: () => {
      if (repositoryId) {
        qc.invalidateQueries({ queryKey: chatSessionQueryKeys.list(repositoryId) });
      }
    },
  });
}

export function useDeleteChatSession(repositoryId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (sessionId: string) => ChatSessionsApi.remove(sessionId),
    onSuccess: () => {
      if (repositoryId) {
        qc.invalidateQueries({ queryKey: chatSessionQueryKeys.list(repositoryId) });
      }
    },
  });
}

/** Optimistically bump a session to the top of the list after activity. */
export function useBumpSessionActivity(repositoryId: string | undefined) {
  const qc = useQueryClient();
  return (sessionId: string) => {
    if (!repositoryId) return;
    qc.invalidateQueries({ queryKey: chatSessionQueryKeys.list(repositoryId) });
    void sessionId;
  };
}

export type { ChatSession };
