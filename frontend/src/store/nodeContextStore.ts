import { create } from "zustand";

/**
 * Cross-feature node context.
 *
 * The Dependency Graph, Architecture view and AI Assistant share a single
 * "what is the user looking at" context so that selecting a node in one
 * surface can be carried into another (e.g. "Ask AI about this file").
 *
 * Context is scoped to a repository: switching repositories clears it so a
 * file from one repo can never leak into another's conversation.
 */
export interface AttachedFile {
  /** Graph node id (stable file id from the backend). */
  id: string;
  path: string;
  language?: string;
}

interface NodeContextState {
  repositoryId: string | null;
  /** Files attached as context for the AI assistant. */
  attached: AttachedFile[];
  /** A question queued for the assistant to send on its next mount. */
  pendingPrompt: string | null;

  /** Attach a file, replacing context if the repository changed. Idempotent. */
  attachFile: (repositoryId: string, file: AttachedFile) => void;
  /** Queue a prompt to auto-send when the assistant opens. */
  setPendingPrompt: (prompt: string | null) => void;
  /** Read and clear the queued prompt (consumed exactly once). */
  consumePendingPrompt: () => string | null;
  removeFile: (id: string) => void;
  clear: () => void;
}

export const useNodeContextStore = create<NodeContextState>((set, get) => ({
  repositoryId: null,
  attached: [],
  pendingPrompt: null,

  attachFile: (repositoryId, file) =>
    set((state) => {
      // Repository changed → start a fresh context.
      const base =
        state.repositoryId === repositoryId
          ? state.attached
          : ([] as AttachedFile[]);
      if (base.some((f) => f.id === file.id)) {
        return { repositoryId, attached: base };
      }
      return { repositoryId, attached: [...base, file] };
    }),

  setPendingPrompt: (prompt) => set({ pendingPrompt: prompt }),

  consumePendingPrompt: () => {
    const prompt = get().pendingPrompt;
    if (prompt !== null) set({ pendingPrompt: null });
    return prompt;
  },

  removeFile: (id) =>
    set((state) => ({ attached: state.attached.filter((f) => f.id !== id) })),

  clear: () => set({ attached: [], pendingPrompt: null }),
}));
