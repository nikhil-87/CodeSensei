/**
 * Session picker for the "Ask AI about this file" flow.
 *
 * Launched from the graph / architecture / inspector surfaces. Lets the user
 * route a file (and an optional starter prompt) into a *new* conversation or
 * an existing one, then deep-links to that session with the file pre-attached.
 */
import { MessageSquare, MessageSquarePlus, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/common/Button";
import { useChatSessions, useCreateChatSession } from "@/hooks/useChatSessions";
import { useNodeContextStore, type AttachedFile } from "@/store/nodeContextStore";

export interface AskAiTarget {
  /** The file to attach as context. Omitted for module/folder-level asks. */
  file?: AttachedFile;
  /** A human label for the subject shown in the dialog header. */
  label: string;
  /** Optional starter question auto-sent when the conversation opens. */
  prompt?: string;
}

interface SessionPickerModalProps {
  repositoryId: string;
  target: AskAiTarget | null;
  onClose: () => void;
}

export function SessionPickerModal({
  repositoryId,
  target,
  onClose,
}: SessionPickerModalProps) {
  const navigate = useNavigate();
  const attachFile = useNodeContextStore((s) => s.attachFile);
  const setPendingPrompt = useNodeContextStore((s) => s.setPendingPrompt);
  const { data: sessionsPage, isLoading } = useChatSessions(
    target ? repositoryId : undefined,
  );
  const createSession = useCreateChatSession(repositoryId);

  if (!target) return null;

  const sessions = sessionsPage?.items ?? [];

  const launch = (sessionId: string) => {
    if (target.file) attachFile(repositoryId, target.file);
    setPendingPrompt(target.prompt ?? null);
    onClose();
    navigate(`/repos/${repositoryId}/chat?session=${sessionId}`);
  };

  const handleNew = async () => {
    const created = await createSession.mutateAsync(undefined);
    launch(created.id);
  };

  return (
    <div
      role="dialog"
      aria-modal
      aria-labelledby="ask-ai-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink-900/40 p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="flex max-h-[80vh] w-full max-w-md flex-col rounded-lg bg-surface p-6 shadow-elev">
        <div className="flex items-start gap-2">
          <div className="rounded-md bg-accent-50 p-1.5 text-accent-600">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h2 id="ask-ai-title" className="text-lg font-semibold text-ink-900">
              Ask AI about this file
            </h2>
            <p className="mt-0.5 truncate text-sm text-ink-500" title={target.label}>
              {target.label}
            </p>
          </div>
        </div>

        <Button
          variant="primary"
          size="sm"
          className="mt-5 w-full justify-center"
          leadingIcon={<MessageSquarePlus className="h-4 w-4" />}
          loading={createSession.isPending}
          onClick={handleNew}
        >
          Start a new conversation
        </Button>

        <div className="mt-5 min-h-0 flex-1 overflow-y-auto">
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-ink-400">
            Or continue an existing one
          </p>
          {isLoading && (
            <p className="px-1 py-2 text-sm text-ink-400">Loading conversations…</p>
          )}
          {!isLoading && sessions.length === 0 && (
            <p className="px-1 py-2 text-sm text-ink-400">
              You have no conversations for this repository yet.
            </p>
          )}
          <ul className="space-y-1">
            {sessions.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => launch(s.id)}
                  className="focus-ring flex w-full items-center gap-2 rounded-md border border-ink-100 px-3 py-2 text-left text-sm text-ink-700 transition-colors hover:border-accent-300 hover:bg-accent-50 hover:text-accent-900"
                >
                  <MessageSquare className="h-4 w-4 shrink-0 text-ink-400" />
                  <span className="min-w-0 flex-1 truncate" title={s.title}>
                    {s.title}
                  </span>
                  <span className="shrink-0 text-[11px] text-ink-400">
                    {new Date(s.last_activity_at).toLocaleDateString()}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="mt-5 flex justify-end">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
        </div>
      </div>
    </div>
  );
}
