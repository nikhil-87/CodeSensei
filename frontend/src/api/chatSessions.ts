/** Persistent chat session client (CRUD + SSE streaming). */
import { apiClient, API_PREFIX } from "@/lib/api";
import { openSse } from "@/lib/sse";
import type {
  ChatMessageRecord,
  ChatSession,
  ChatSessionCreateInput,
  ChatSessionUpdateInput,
  ChatTokenEvent,
  Paginated,
  SessionChatRequest,
} from "@/types/api";

export const ChatSessionsApi = {
  list: async (
    repositoryId: string,
    params: { page?: number; page_size?: number } = {},
  ): Promise<Paginated<ChatSession>> => {
    const { data } = await apiClient.get<Paginated<ChatSession>>(
      `/repositories/${repositoryId}/chat-sessions`,
      { params },
    );
    return data;
  },

  create: async (
    repositoryId: string,
    input: ChatSessionCreateInput = {},
  ): Promise<ChatSession> => {
    const { data } = await apiClient.post<ChatSession>(
      `/repositories/${repositoryId}/chat-sessions`,
      input,
    );
    return data;
  },

  get: async (sessionId: string): Promise<ChatSession> => {
    const { data } = await apiClient.get<ChatSession>(`/chat-sessions/${sessionId}`);
    return data;
  },

  rename: async (
    sessionId: string,
    input: ChatSessionUpdateInput,
  ): Promise<ChatSession> => {
    const { data } = await apiClient.patch<ChatSession>(
      `/chat-sessions/${sessionId}`,
      input,
    );
    return data;
  },

  remove: async (sessionId: string): Promise<void> => {
    await apiClient.delete(`/chat-sessions/${sessionId}`);
  },

  messages: async (
    sessionId: string,
    params: { page?: number; page_size?: number } = {},
  ): Promise<Paginated<ChatMessageRecord>> => {
    const { data } = await apiClient.get<Paginated<ChatMessageRecord>>(
      `/chat-sessions/${sessionId}/messages`,
      { params },
    );
    return data;
  },

  /**
   * Stream an answer within a session. Yields one ``ChatTokenEvent`` per
   * server event; iteration ends when the server emits ``done`` or ``error``.
   */
  streamChat: async function* (
    sessionId: string,
    request: SessionChatRequest,
    signal?: AbortSignal,
  ): AsyncIterableIterator<ChatTokenEvent> {
    const stream = openSse({
      url: `${API_PREFIX}/chat-sessions/${sessionId}/chat`,
      method: "POST",
      body: request,
      signal,
    });
    for await (const evt of stream) {
      try {
        const parsed = JSON.parse(evt.data) as ChatTokenEvent;
        yield parsed;
        if (parsed.event === "done" || parsed.event === "error") return;
      } catch {
        // skip malformed
      }
    }
  },
};
